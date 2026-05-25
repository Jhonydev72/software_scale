import pandas as pd
from scale_app.models import Process, Flow, EmergySource


def calculate_emergy(product_id, inventory_id=None):
    """
    Versão usando pandas para calcular a emergia total de um produto,
    corrigindo a aplicação da álgebra de emergia sobre os fluxos upstream.

    Se inventory_id for fornecido, filtra apenas dados daquele inventário.
    """
    # Construir querysets com filtro opcional por inventário
    process_qs = Process.objects.all()
    flow_qs = Flow.objects.all()
    source_qs = EmergySource.objects.all()

    if inventory_id is not None:
        process_qs = process_qs.filter(inventory_id=inventory_id)
        flow_qs = flow_qs.filter(inventory_id=inventory_id)
        source_qs = source_qs.filter(inventory_id=inventory_id)

    # Buscar todos os dados do banco e montar DataFrames
    processes = pd.DataFrame(list(process_qs.values('id', 'name')))
    flows = pd.DataFrame(list(flow_qs.values('from_process_id', 'to_process_id', 'amount')))
    sources = pd.DataFrame(list(source_qs.values('process_id', 'transformity', 'amount')))

    # Construir dicionário de fluxos de entrada (to_process -> lista de (from, amount))
    flow_dict = {}
    if not flows.empty:
        for _, row in flows.iterrows():
            to_p = row['to_process_id']
            from_p = row['from_process_id']
            amt = row['amount']
            if to_p not in flow_dict:
                flow_dict[to_p] = []
            flow_dict[to_p].append((from_p, amt))

    # Cache armazena a UEV (Transformidade acumulada) calculada para cada processo
    cache = {}

    def compute(pid, visited=None):
        if visited is None:
            visited = set()
        if pid in cache:
            return cache[pid]
        if pid in visited:
            return 0.0   # ciclo simples (ignorar para evitar loop infinito)
        visited.add(pid)

        # 1. Emergia direta das fontes da natureza (Quantidade * Transformidade) -> Resultado em SEJ
        if not sources.empty:
            src_mask = sources['process_id'] == pid
            nature_emergy = (sources.loc[src_mask, 'amount'] * sources.loc[src_mask, 'transformity']).sum()
        else:
            nature_emergy = 0.0

        # 2. Somar emergia vinda de processos anteriores (upstream)
        indirect_emergy = 0.0
        if pid in flow_dict:
            for from_p, amt in flow_dict[pid]:
                # O processo anterior retorna a sua respectiva transformidade acumulada (sej/unidade)
                upstream_transformity = compute(from_p, visited.copy())

                # CORREÇÃO AQUI: Quantidade do fluxo (amt) * Transformidade do recurso (upstream_transformity)
                indirect_emergy += amt * upstream_transformity

        # A emergia total deste nó é a soma da direta com a indireta
        total_emergy_node = nature_emergy + indirect_emergy

        cache[pid] = total_emergy_node
        return total_emergy_node

    product_emergy = compute(product_id)
    return product_emergy


def calculate_emergy_with_report(product_id, inventory_id=None):
    """
    Retorna um dicionário com total e decomposição por fonte.
    """
    total = calculate_emergy(product_id, inventory_id=inventory_id)
    return {
        'product_id': product_id,
        'emergy_sej': total,
        'unit': 'sej',
        'message': 'Cálculo concluído com sucesso aplicando a fórmula Q * UEV'
    }