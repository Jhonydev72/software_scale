import json
import pandas as pd

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Process, Flow, EmergySource


# ============================================================
# INDEX
# ============================================================
def index(request):
    return render(request, 'scale_app/index.html')


# ============================================================
# LISTAR PROCESSOS
# ============================================================
def list_processes(request):
    processes = Process.objects.values('id', 'name', 'description')
    return JsonResponse(list(processes), safe=False)


# ============================================================
# FUNÇÕES AUXILIARES (ANTI-ERRO)
# ============================================================
def safe_float(value):
    """Evita erro de NULL / NaN vindo do Excel"""
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except:
        return 0.0


# ============================================================
# UPLOAD LCI FINAL ROBUSTO
# ============================================================
@csrf_exempt
def upload_lci(request):

    if request.method != 'POST' or not request.FILES.get('file'):
        return JsonResponse({'error': 'Nenhum arquivo enviado'}, status=400)

    uploaded_file = request.FILES['file']
    extension = uploaded_file.name.split('.')[-1].lower()

    # limpar banco
    Flow.objects.all().delete()
    EmergySource.objects.all().delete()
    Process.objects.all().delete()

    try:
        flows_df = None
        sources_df = None

        # =========================
        # CSV
        # =========================
        if extension == 'csv':
            df = pd.read_csv(uploaded_file)
            df.columns = [c.lower().strip() for c in df.columns]
            flows_df = df

        # =========================
        # EXCEL
        # =========================
        elif extension in ['xls', 'xlsx']:
            xl = pd.ExcelFile(uploaded_file)

            print("ABAS:", xl.sheet_names)

            for sheet in xl.sheet_names:
                temp_df = pd.read_excel(xl, sheet)
                temp_df.columns = [str(c).lower().strip() for c in temp_df.columns]

                cols = temp_df.columns.tolist()

                print("\nABA:", sheet)
                print("COLUNAS:", cols)

                # =====================
                # FLUXOS (SEU FORMATO REAL)
                # =====================
                if flows_df is None:
                    if (
                        'processo_destino_id' in cols and
                        'insumo_fluxo' in cols and
                        'quantidade' in cols
                    ):
                        flows_df = temp_df

                # =====================
                # FONTES
                # =====================
                if sources_df is None:
                    if (
                        'uev_valor' in cols or
                        'transformity' in cols
                    ):
                        sources_df = temp_df

        else:
            return JsonResponse(
                {'error': 'Formato não suportado (use csv, xls ou xlsx)'},
                status=400
            )

        # =========================
        # VALIDAÇÃO
        # =========================
        if flows_df is None:
            return JsonResponse({'error': 'Tabela de fluxos não encontrada'}, status=400)

        # =========================
        # GERAR PROCESSOS AUTOMATICAMENTE
        # =========================
        process_ids = pd.unique(
            flows_df[['id', 'processo_destino_id']].values.ravel()
        )
        process_ids = [p for p in process_ids if pd.notna(p)]

        processes_df = pd.DataFrame({
            'id': process_ids,
            'nome': process_ids
        })

        # =========================
        # SALVAR PROCESSOS
        # =========================
        for _, row in processes_df.iterrows():
            Process.objects.create(
                id=row['id'],
                name=row['nome'],
                description=''
            )

        # =========================
        # SALVAR FLUXOS
        # =========================
        for _, row in flows_df.iterrows():
            Flow.objects.create(
                from_process_id=row.get('id'),
                to_process_id=row.get('processo_destino_id'),
                amount=safe_float(row.get('quantidade')),
                unit=row.get('unidade', '')
            )

        # =========================
        # SALVAR FONTES (SEM ERRO DE NULL)
        # =========================
        if sources_df is not None:
            for _, row in sources_df.iterrows():

                transformity = safe_float(
                    row.get('uev_valor') or row.get('transformity')
                )

                amount = safe_float(row.get('quantidade'))

                EmergySource.objects.create(
                    process_id=row.get('id'),
                    source_name=row.get('insumo_fluxo', 'fonte'),
                    transformity=transformity,
                    amount=amount,
                    unit=row.get('unidade', '')
                )

        return JsonResponse({
            'message': 'Importação concluída com sucesso!',
            'processos': len(processes_df)
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================
# CALCULO EMERGIA
# ============================================================
@csrf_exempt
def calculate_api(request):

    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)

    try:
        data = json.loads(request.body)
        product_id = data.get('productId')

        if not product_id:
            return JsonResponse({'error': 'productId é obrigatório'}, status=400)

        return JsonResponse(calculate_emergy(product_id))

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================
# EMERGIA RECURSIVA
# ============================================================
def calculate_emergy(product_id):

    sources = EmergySource.objects.filter(process_id=product_id)

    total = sum(
        (s.amount or 0) * (s.transformity or 0)
        for s in sources
    )

    flows = Flow.objects.filter(to_process_id=product_id)

    for f in flows:
        upstream = calculate_emergy(f.from_process_id)['emergy_sej']
        total += upstream * (f.amount or 0)

    return {
        'productId': product_id,
        'emergy_sej': float(total),
        'unit': 'sej'
    }