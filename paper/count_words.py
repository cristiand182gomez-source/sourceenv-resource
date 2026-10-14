"""Count the complete Markdown manuscript and hash-mapped SVG figure labels.

Unmapped images, changed assets, path-based text, HTML, footnotes or fenced
blocks fail closed for manual audit rather than silently losing visible text.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET

IMAGE = re.compile(r"!\[([^\]\n]*)\]\(([^)\s]+)\)")
LINK = re.compile(r"\[([^\]]+)\]\(([^)\n]+)\)")

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def asset(root, name):
    path=(root/name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("Figure must be a retained local file: "+name)
    return path

def svg_labels(path):
    root=ET.parse(path).getroot()
    allowed={"svg","title","desc","rect","text","tspan","line","polyline","polygon","circle","ellipse","g"}
    labels=[]
    for el in root.iter():
        name=el.tag.rsplit("}",1)[-1]
        if name not in allowed:
            raise ValueError(f"Unsupported SVG element {name}: audit figure text first")
        if any(k.rsplit("}",1)[-1] in {"style","href"} for k in el.attrib):
            raise ValueError("Styled or externally referenced SVG requires an audit")
        if name=="text":
            labels.append("".join(el.itertext()).strip())
    if not labels:
        raise ValueError("No visible text nodes; do not count text paths as zero words")
    return "\n".join(labels)

def figures(text,root):
    found=list(IMAGE.finditer(text))
    if "![" in IMAGE.sub("",text):
        raise ValueError("Unsupported image syntax: map image and visible text first")
    if not found:
        return []
    manifest=json.loads((root/"figures/FIGURE_MANIFEST.json").read_text(encoding="utf-8"))
    rows=[]
    for image in found:
        name=image.group(2);item=manifest["images"].get(name)
        if item is None:
            raise ValueError("Unmapped image: "+name)
        image_path=asset(root,name);source=asset(root,item["text_source"])
        if sha(image_path)!=item["image_sha256"] or sha(source)!=item["text_source_sha256"]:
            raise ValueError("Figure identity differs from audited manifest: "+name)
        if source.suffix.lower()!=".svg":
            raise ValueError("Figure text source must be SVG")
        labeltext=svg_labels(source)
        rows.append({"image":name,"image_sha256":sha(image_path),"text_source":item["text_source"],
                     "text_source_sha256":sha(source),"visible_text":labeltext,"visible_words":len(labeltext.split())})
    return rows

def visible(text):
    if re.search(r"<[^\n>]+>|^\s*```|^\[\^[^\]]+\]:",text,re.M):
        raise ValueError("Unsupported main-file construct: audit its visible text first")
    text=IMAGE.sub(lambda m:m.group(1),text)
    text=LINK.sub(lambda m:m.group(1),text)
    result=[]
    for line in text.splitlines():
        if re.fullmatch(r"\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)*\|?\s*",line):
            continue
        line=re.sub(r"^\s*#{1,6}\s+","",line)
        line=re.sub(r"^\s*(?:[-+*]|\d+\.)\s+","",line)
        line=line.replace("**","").replace("`","").replace("*","")
        if line.lstrip().startswith("|"):
            line=line.replace("|"," ")
        result.append(line)
    return "\n".join(result)

def count(path):
    raw=path.read_text(encoding="utf-8")
    parts=[];section="Title";buffer=[]
    for line in raw.splitlines(keepends=True):
        if line.startswith("## "):
            parts.append((section,"".join(buffer)));section=line[3:].strip();buffer=[line]
        else:
            buffer.append(line)
    parts.append((section,"".join(buffer)))
    rows=[];image_rows=[]
    for name,text in parts:
        imgs=figures(text,path.parent);nfig=sum(r["visible_words"] for r in imgs)
        gross=len(text.split());shown=len(visible(text).split())
        rows.append({"section":name,"raw_whitespace":gross,"visible_whitespace":shown,"figure_visible_words":nfig,
                     "conservative":max(gross,shown)+nfig})
        image_rows.extend(imgs)
    gross=len(raw.split());shown=len(visible(raw).split());nfig=sum(r["visible_words"] for r in image_rows)
    conservative=sum(r["conservative"] for r in rows)
    return {"document":path.name,"document_sha256":sha(path),"counter_sha256":sha(Path(__file__)),
        "method":"split on Unicode whitespace; Markdown presentation syntax/link destinations stripped for visible count; sum per-section max(raw,visible) PLUS all visible SVG figure-label words for each embedded mapped image",
        "scope":"entire DRAFT.md: title, every section, tables, captions, notes, references and visible figure text; no main-text exemptions",
        "not_main":"SUPPLEMENT.md and separate supporting files; image alt labels remain conservatively included; SVG title/desc metadata are not visible labels",
        "figure_manifest_sha256":sha(path.parent/"figures/FIGURE_MANIFEST.json") if image_rows else None,
        "figures":image_rows,"sections":rows,
        "total":{"raw_whitespace":gross,"visible_whitespace":shown,"figure_visible_words":nfig,"visible_with_figures":shown+nfig,"conservative":conservative},
        "target":2900,"maximum":3000,"within_target":conservative<=2900,"within_maximum":conservative<=3000}

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("document",type=Path,nargs="?",default=Path(__file__).resolve().parent/"DRAFT.md")
    ap.add_argument("--output",type=Path)
    args=ap.parse_args();result=count(args.document)
    output=args.output or args.document.with_name("WORD_COUNT.json")
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps(result["total"]))
    if not result["within_maximum"]:
        raise SystemExit("Main document exceeds 3,000 words: not a final delivery")
