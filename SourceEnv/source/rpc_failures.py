"""Only a proved owner deadline and closed process permit censoring."""
class ModelRPCFailure(RuntimeError):
    def __init__(self,result):super().__init__(result.get('error','RPC_FAILED'));self.result=result

def cancellation_proved(result):
    p=result.get('closure') or {}
    return (result.get('deadline_expired') is True and p.get('process_terminated') is True
            and p.get('port_closed') is True and p.get('no_active_request') is True)
