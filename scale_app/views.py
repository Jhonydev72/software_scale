import os
import json
import pandas as pd
import numpy as np

from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, Http404
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
# FUNÇÕES AUXILIARES
# ============================================================
def safe_float(value):
    """Evita erro com NULL, NaN ou string inválida"""
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except:
        return 0.0


# ============================================================
# UPLOAD LCI
# ============================================================
@csrf_exempt
def upload_lci(request):

    if request.method != 'POST' or not request.FILES.get('file'):
        return JsonResponse({'error': 'Nenhum arquivo enviado'}, status=400)

    uploaded_file = request.FILES['file']
    extension = uploaded_file.name.split('.')[-1].lower()

    # Limpar banco
    Flow.objects.all().delete()
    EmergySource.objects.all().delete()
    Process.objects.all().delete()

    try:

        # ====================================================
        # LEITURA DO ARQUIVO
        # ====================================================
        if extension == 'csv':
            df = pd.read_csv(uploaded_file)

        elif extension in ['xls', 'xlsx']:
            df = pd.read_excel(uploaded_file)

        else:
            return JsonResponse({
                'error': 'Formato não suportado. Use csv, xls ou xlsx'
            }, status=400)

        # ====================================================
        # NORMALIZAR COLUNAS
        # ====================================================
        df.columns = [str(c).strip().lower() for c in df.columns]

        print("COLUNAS ENCONTRADAS:")
        print(df.columns.tolist())

        # ====================================================
        # VALIDAR COLUNAS IMPORTANTES
        # ====================================================
        required_columns = [
            'processo_destino_id',
            'nome_processo_destino',
            'insumo_fluxo',
            'quantidade'
        ]

        for col in required_columns:
            if col not in df.columns:
                return JsonResponse({
                    'error': f'Coluna obrigatória não encontrada: {col}'
                }, status=400)

        # ====================================================
        # CRIAR PROCESSOS
        # ====================================================
        processos_unicos = (
            df[['processo_destino_id', 'nome_processo_destino']]
            .dropna()
            .drop_duplicates()
        )

        for _, row in processos_unicos.iterrows():

            process_id = int(row['processo_destino_id'])

            Process.objects.get_or_create(
                id=process_id,
                defaults={
                    'name': str(row['nome_processo_destino']).strip(),
                    'description': ''
                }
            )

        # ====================================================
        # MAPEAR SAÍDAS
        # ====================================================
        mapa_saidas = {}

        if 'tipo_fluxo' in df.columns:

            df_saidas = df[
                df['tipo_fluxo']
                .astype(str)
                .str.strip()
                .str.lower() == 'saída'
            ]

            for _, row in df_saidas.iterrows():

                insumo = str(row['insumo_fluxo']).strip()

                mapa_saidas[insumo] = int(
                    row['processo_destino_id']
                )

        # ====================================================
        # PROCESSAR LINHAS
        # ====================================================
        for _, row in df.iterrows():

            to_process_id = int(row['processo_destino_id'])

            insumo = str(
                row.get('insumo_fluxo', '')
            ).strip()

            quantidade = safe_float(
                row.get('quantidade')
            )

            unidade = str(
                row.get('unidade', '')
            ).strip()

            uev = safe_float(
                row.get('uev_valor')
            )

            # ================================================
            # É FONTE EXTERNA
            # ================================================
            if uev > 0:

                EmergySource.objects.create(
                    process_id=to_process_id,
                    source_name=insumo,
                    transformity=uev,
                    amount=quantidade,
                    unit=unidade
                )

            # ================================================
            # É FLUXO INTERNO
            # ================================================
            else:

                from_process_id = mapa_saidas.get(insumo)

                if from_process_id:

                    Flow.objects.create(
                        from_process_id=from_process_id,
                        to_process_id=to_process_id,
                        amount=quantidade,
                        unit=unidade
                    )

                else:
                    # fallback seguro
                    EmergySource.objects.create(
                        process_id=to_process_id,
                        source_name=insumo,
                        transformity=0.0,
                        amount=quantidade,
                        unit=unidade
                    )

        return JsonResponse({
            'message': 'Importação concluída com sucesso!',
            'processos': Process.objects.count(),
            'flows': Flow.objects.count(),
            'sources': EmergySource.objects.count()
        })

    except Exception as e:

        print("ERRO:", str(e))

        return JsonResponse({
            'error': str(e)
        }, status=500)


# ============================================================
# API DE CÁLCULO
# ============================================================
@csrf_exempt
def calculate_api(request):

    if request.method != 'POST':
        return JsonResponse({
            'error': 'Método não permitido'
        }, status=405)

    try:

        data = json.loads(request.body)

        product_id = data.get('productId')

        if not product_id:
            return JsonResponse({
                'error': 'productId é obrigatório'
            }, status=400)

        result = calculate_emergy(product_id)

        return JsonResponse(result)

    except Exception as e:

        return JsonResponse({
            'error': str(e)
        }, status=500)


# ============================================================
# CÁLCULO RECURSIVO
# ============================================================
def calculate_emergy(product_id, cache=None):

    if cache is None:
        cache = {}

    if product_id in cache:
        return cache[product_id]

    # ========================================================
    # FONTES DIRETAS
    # ========================================================
    sources = EmergySource.objects.filter(
        process_id=product_id
    )

    total = sum(
        (s.amount or 0) * (s.transformity or 0)
        for s in sources
    )

    # ========================================================
    # FLUXOS DE ENTRADA
    # ========================================================
    flows = Flow.objects.filter(
        to_process_id=product_id
    )

    for flow in flows:

        upstream = calculate_emergy(
            flow.from_process_id,
            cache
        )['emergy_sej']

        total += upstream * (flow.amount or 0)

    result = {
        'productId': product_id,
        'emergy_sej': float(total),
        'unit': 'sej'
    }

    cache[product_id] = result

    return result


# ============================================================
# DOWNLOAD TEMPLATE
# ============================================================
def download_template(request):

    file_path = os.path.join(
        settings.BASE_DIR,
        'Planilha_Calculos_Emergeticos.xlsx'
    )

    if os.path.exists(file_path):

        with open(file_path, 'rb') as excel:

            response = HttpResponse(
                excel.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

            response['Content-Disposition'] = (
                'attachment; filename="Planilha_Calculos_Emergeticos.xlsx"'
            )

            return response

    raise Http404(
        "Arquivo Planilha_Calculos_Emergeticos.xlsx não encontrado."
    )