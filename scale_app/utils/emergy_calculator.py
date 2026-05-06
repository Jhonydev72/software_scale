import pandas as pd
from scale_app.models import Process, Flow, EmergySource

def calculate_emergy(product_id):
    """
    Versão usando pandas (mais rápida) para calcular a emergia total de um produto.
    """
    # Buscar todos os dados do banco e montar DataFrames
    processes = pd.DataFrame(list(Process.objects.values('id', 'name')))
    flows = pd.DataFrame(list(Flow.objects.values('from_process_id', 'to_process_id', 'amount')))
    sources = pd.DataFrame(list(EmergySource.objects.values('process_id', 'transformity', 'amount')))
    
    # Construir dicionário de fluxos de entrada (to_process -> lista de (from, amount))
    flow_dict = {}
    for _, row in flows.iterrows():
        to_p = row['to_process_id']
        from_p = row['from_process_id']
        amt = row['amount']
        if to_p not in flow_dict:
            flow_dict[to_p] = []
        flow_dict[to_p].append((from_p, amt))
    
    # Cálculo recursivo com cache (evita recalcular sub-grafos)
    cache = {}
    def compute(pid, visited=None):
        if visited is None:
            visited = set()
        if pid in cache:
            return cache[pid]
        if pid in visited:
            return 0.0   # ciclo simples (ignorar)
        visited.add(pid)
        
        # Emergia direta das fontes emergéticas associadas a este processo
        src_mask = sources['process_id'] == pid
        total = (sources.loc[src_mask, 'amount'] * sources.loc[src_mask, 'transformity']).sum()
        
        # Somar emergia vinda de processos anteriores (upstream)
        if pid in flow_dict:
            for from_p, amt in flow_dict[pid]:
                upstream_emergy = compute(from_p, visited.copy())
                total += upstream_emergy * amt
        
        cache[pid] = total
        return total
    
    product_emergy = compute(product_id)
    return product_emergy

def calculate_emergy_with_report(product_id):
    """
    Retorna um dicionário com total e decomposição por fonte (para relatórios opcionais).
    """
    # … implementação mais detalhada se quiser
    # Basta seguir a mesma lógica mas armazenar contribuições por fonte
    total = calculate_emergy(product_id)
    return {
        'product_id': product_id,
        'emergy_sej': total,
        'unit': 'sej',
        'message': 'Cálculo concluído'
    }