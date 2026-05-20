import os
import json
import pandas as pd
import numpy as np

from django.conf import settings
from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .models import Process, Flow, EmergySource

# ============================================================
# FUNÇÃO INDEX
# ============================================================
def index(request):
    """Página inicial - renderiza o template HTML"""
    return render(request, 'scale_app/index.html')
# ============================================================

def list_processes(request):
    """Lista todos os processos em JSON"""
    processes = Process.objects.values('id', 'name', 'description')
    return JsonResponse(list(processes), safe=False)

@csrf_exempt
def upload_lci(request):
    """Importa arquivo CSV ou Excel e popula o banco de dados baseado em colunas"""
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        file_name = uploaded_file.name
        extension = file_name.split('.')[-1].lower()
        
        # Limpar dados antigos
        Flow.objects.all().delete()
        EmergySource.objects.all().delete()
        Process.objects.all().delete()
        
        try:
            # Ler o arquivo de aba única
            if extension == 'csv':
                df = pd.read_csv(uploaded_file)
            elif extension in ['xls', 'xlsx']:
                df = pd.read_excel(uploaded_file)
            else:
                return JsonResponse({'error': 'Formato não suportado. Use .csv, .xls ou .xlsx'}, status=400)
            
            # Normalizar os nomes das colunas para evitar erros de case sensitivity
            df.columns = [str(c).strip() for c in df.columns]
            
            # 1. Inserir Processos (Filtrando os IDs únicos de destino)
            processos_unicos = df.dropna(subset=['Processo_Destino_ID']).drop_duplicates(subset=['Processo_Destino_ID'])
            for _, row in processos_unicos.iterrows():
                Process.objects.create(
                    id=int(row['Processo_Destino_ID']),
                    name=str(row['Nome_Processo_Destino']).strip(),
                    description=""
                )
            
            # 2. Mapear as "Saídas" para vincular os Fluxos Internos (Flows) depois
            # Salva num dicionário qual Insumo é produzido por qual Processo_ID
            df_saidas = df[df['Tipo_Fluxo'].astype(str).str.strip().str.lower() == 'saída']
            mapa_saidas = {}
            for _, row in df_saidas.iterrows():
                insumo = str(row['Insumo_Fluxo']).strip()
                mapa_saidas[insumo] = int(row['Processo_Destino_ID'])
            
            # 3. Processar as "Entradas" para popular Fontes (EmergySource) e Fluxos (Flow)
            df_entradas = df[df['Tipo_Fluxo'].astype(str).str.strip().str.lower() == 'entrada']
            
            for _, row in df_entradas.iterrows():
                to_process_id = int(row['Processo_Destino_ID'])
                insumo = str(row['Insumo_Fluxo']).strip()
                quantidade = float(row['Quantidade']) if pd.notna(row['Quantidade']) else 0.0
                unidade = str(row['Unidade']).strip() if pd.notna(row['Unidade']) else ""
                
                val_uev = row.get('UEV_Valor')
                # Tratamento robusto para identificar se a UEV é uma fonte externa válida
                if pd.notna(val_uev) and str(val_uev).strip().lower() not in ['null', 'nan', 'none', '']:
                    EmergySource.objects.create(
                        process_id=to_process_id,
                        source_name=insumo,
                        transformity=float(val_uev),
                        amount=quantidade,
                        unit=unidade
                    )
                
                # Se tiver UEV declarada na linha, é uma Fonte Externa (EmergySource)
                if pd.notna(val_uev) and str(val_uev).strip().lower() not in ['null', 'nan', '']:
                    EmergySource.objects.create(
                        process_id=to_process_id,
                        source_name=insumo,
                        transformity=float(val_uev),
                        amount=quantidade,
                        unit=unidade
                    )
                else:
                    # Se não tem UEV, é um Fluxo que vem de outro processo (Flow)
                    from_process_id = mapa_saidas.get(insumo)
                    
                    if from_process_id:
                        Flow.objects.create(
                            from_process_id=from_process_id,
                            to_process_id=to_process_id,
                            amount=quantidade,
                            unit=unidade
                        )
                    else:
                        # Fallback: Se a origem não foi mapeada, salva como Fonte Externa com UEV 0 para não perder o dado
                        EmergySource.objects.create(
                            process_id=to_process_id,
                            source_name=insumo,
                            transformity=0.0,
                            amount=quantidade,
                            unit=unidade
                        )
            
            return JsonResponse({
                'message': 'Dados importados com sucesso!', 
                'processos': Process.objects.count()
            })
        
        except Exception as e:
            return JsonResponse({'error': f"Erro no processamento da planilha: {str(e)}"}, status=500)
    
    return JsonResponse({'error': 'Nenhum arquivo enviado'}, status=400)

@csrf_exempt
def calculate_api(request):
    """Calcula emergia para um produto (versão simplificada)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('productId')
            if not product_id:
                return JsonResponse({'error': 'productId é obrigatório'}, status=400)
            
            # Calcular emergia de forma recursiva
            result = calculate_emergy(product_id)
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método não permitido. Use POST.'}, status=405)

def calculate_emergy(product_id):
    """Função recursiva para calcular emergia total de um processo"""
    # Buscar fontes emergéticas diretas do processo
    sources = EmergySource.objects.filter(process_id=product_id)
    total = 0
    for source in sources:
        total += source.amount * source.transformity
    
    # Buscar fluxos de entrada (de outros processos para este)
    incoming_flows = Flow.objects.filter(to_process_id=product_id)
    for flow in incoming_flows:
        # Pega a emergia total do processo anterior
        upstream_emergy = calculate_emergy(flow.from_process_id)['emergy_sej']
        
        # Nota sobre álgebra emergética: Aqui estamos mantendo a sua fórmula original (Multiplicando pelo Amount). 
        # Dependendo da metodologia, se upstream_emergy for a emergia *total*, multiplicar pelo amount pode inflar os números. 
        total += upstream_emergy * flow.amount
    
    return {
        'productId': product_id,
        'emergy_sej': float(total),
        'unit': 'sej'
    }

# ============================================================
# NOVA FUNÇÃO PARA DOWNLOAD DA PLANILHA (CORRIGIDA)
# ============================================================
def download_template(request):
    """Disponibiliza a planilha modelo em Excel para o usuário baixar e preencher"""
    
    file_path = os.path.join(settings.BASE_DIR, 'Planilha_Calculos_Emergeticos.xlsx')
    
    if os.path.exists(file_path):
        with open(file_path, 'rb') as excel:
            response = HttpResponse(
                excel.read(), 
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="Planilha_Calculos_Emergeticos.xlsx"'
            return response
    else:
        raise Http404("O arquivo de template (Planilha_Calculos_Emergeticos.xlsx) não foi encontrado no servidor.")