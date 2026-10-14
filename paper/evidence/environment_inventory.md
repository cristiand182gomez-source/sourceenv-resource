# Table 4 — Declared environment and pinned components

| Component | Value | Source/field |
| --- | --- | --- |
| Application OS | Debian 13.7 | environment.json /historical/debian_version |
| Application Python | 3.13.5 (main, Aug 10 2026, 12:06:59) [GCC 14.2.0] | environment.json /historical/python |
| Bubblewrap | bubblewrap 0.12.0 | environment.json /readonly_readback/bubblewrap_version; same SHA as retained binary |
| Bubblewrap SHA256 | 573236e5328ac2ebb08f59ae3a9805b4f8d12bdef14be8af4450d5463294985f | environment.json /retained_binary/bubblewrap_sha256 |
| Application contract | stateless-cli-v1; fresh auxiliaries per invocation; read-only application mount; COLUMNS=100 | r3_proposal.json /application_environment; policy.json /isolation |
| Model owner OS | Windows CPU executable (not the Debian candidate environment) | server_C3.json and server_C1.json, original executable recorded in SOURCE_INDEX |
| llama.cpp | b11429 | r3_proposal.json /configurations/C3/model/build |
| llama.cpp commit | d81235049384534c167caea52b85a694f6103d14 | r3_proposal.json /configurations/C3/model/engine_commit |
| llama.cpp binary SHA256 | 7e236243c9b670c6a49410c03186fd575c57a0efe3fd8a21d8727503d571d5b6 | r3_proposal.json /configurations/C3/model/engine_sha256 |
| C3 GGUF | 676c35070db6dbe52f93e9c864ee0fba4eddea94b9c875d9cb10daff453fbaee | r3_proposal.json /configurations/C3/model/model_sha256 |
| C3 server flags | llama-server -m <GGUF> --alias sourceenv-v05-c3 --offline --host 127.0.0.1 --port 52517 -ngl 0 -t 6 -tb 6 -c 32768 -np 1 --no-context-shift --jinja --reasoning off --reasoning-format deepseek --no-reasoning-preserve --no-warmup --no-webui --cache-prompt --cache-ram 0 --timeout 14400 --log-colors off | server_C3.json /argv; only paths replaced |
| C1 GGUF | 8e30dff3ac4c8434c49a7036fa15564bdbb6044e42bf04550bf1a096ad7e6a52 | r3_proposal.json /configurations/C1/model/model_sha256 |
| C1 server flags | llama-server -m <GGUF> --alias sourceenv-v05-c3 --offline --host 127.0.0.1 --port 64051 -ngl 0 -t 6 -tb 6 -c 32768 -np 1 --no-context-shift --jinja --reasoning off --reasoning-format deepseek --no-reasoning-preserve --no-warmup --no-webui --cache-prompt --cache-ram 0 --timeout 14400 --log-colors off | server_C1.json /argv; only paths replaced |

## Exact wheel inventory

| Distribution | Version | Wheel | SHA256 |
| --- | --- | --- | --- |
| click | 8.1.8 | click-8.1.8-py3-none-any.whl | 63c132bbbed01578a06712a2d1f497bb62d9c1c0d329b7903a866228027263b2 |
| click | 8.2.0 | click-8.2.0-py3-none-any.whl | 6b303f0b2aa85f1cb4e5303078fadcbcd4e476f114fab9b5007005711839325c |
| markdown_it_py | 3.0.0 | markdown_it_py-3.0.0-py3-none-any.whl | 355216845c60bd96232cd8d8c40e8f9765cc86f46880e43a8fd22dc1a1a8cab1 |
| mdurl | 0.1.2 | mdurl-0.1.2-py3-none-any.whl | 84008a41e51615a49fc9966191ff91509e3c40b939176e643fd50a5c2196b8f8 |
| pygments | 2.18.0 | pygments-2.18.0-py3-none-any.whl | b8e6aca0523f3ab76fee51799c488e38782ac06eafcf95e7ba832985c8e7b13a |
| rich | 13.9.4 | rich-13.9.4-py3-none-any.whl | 6049d5e6ec054bf2779ab3358186963bac2ea89175919d699e378b99738c2a90 |
| shellingham | 1.5.4 | shellingham-1.5.4-py2.py3-none-any.whl | 7ecfff8f2fd72616f7481040475a65b2bf8af90a56c89140852d1120324e8686 |
| typer | 0.15.3 | typer-0.15.3-py3-none-any.whl | c86a65ad77ca531f03de08d1b9cb67cd09ad02ddddf4b34745b5008f43b239bd |
| typer | 0.16.0 | typer-0.16.0-py3-none-any.whl | 1f79bed11d4d02d4310e3c1b7ba594183bcedb0ac73b27a9e5f28f6fb5b98855 |
| typing_extensions | 4.12.2 | typing_extensions-4.12.2-py3-none-any.whl | 04e5ca0351e0f3f85c6853954072df659d0d13fac324d0072316b67d7794700d |

## Three agent-selectable profiles

| Profile | Typer | Click | Allowed implicit-help rc | Automatic-help reference rc |
| --- | --- | --- | --- | --- |
| typer0153_click820 | 0.15.3 | 8.2.0 | [0, 2] | 2 |
| typer0153_click818 | 0.15.3 | 8.1.8 | [0, 2] | 0 |
| typer0160_click820 | 0.16.0 | 8.2.0 | [0, 2] | 2 |

Two additional initial-only environments omit Typer or Rich; they are not selectable repair profiles. The Bubblewrap version was read without applications and matched the historical binary SHA256; the original run did not retain its version string. This is the observed original environment, not evidence of a clean Debian installation. The model server ran on Windows; the candidate apps ran only in Debian/Bubblewrap. OFF did not guarantee zero reasoning tokens: C3 emitted 1,026 thought tokens, a subset of its 26,277 generated tokens. No reasoning was reinjected. The policy prose says implicit help has 'no traceback', but the frozen oracle does not explicitly test that predicate. The erratum is preserved; no frozen bytes were changed.
