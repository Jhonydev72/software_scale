from django.shortcuts import render

# Create your views here.
import json
import pandas as pd
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Process, Flow, EmergySource

# ============================================================
# FUNÇÃO INDEX - É ESTA QUE ESTÁ FALTANDO NO SEU ARQUIVO
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
    """Importa arquivo CSV ou Excel e popula o banco de dados"""
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        file_name = uploaded_file.name
        extension = file_name.split('.')[-1].lower()
        
        # Limpar dados antigos
        Flow.objects.all().delete()
        EmergySource.objects.all().delete()
        Process.objects.all().delete()
        
        try:
            if extension == 'csv':
                df = pd.read_csv(uploaded_file)
                # Separar os dados pelo campo 'tipo'
                processes_df = df[df['tipo'] == 'processo']
                flows_df = df[df['tipo'] == 'fluxo']
                sources_df = df[df['tipo'] == 'fonte']
                
            elif extension in ['xls', 'xlsx']:
                xl = pd.ExcelFile(uploaded_file)
                processes_df = pd.read_excel(xl, 'processos')
                flows_df = pd.read_excel(xl, 'fluxos')
                sources_df = pd.read_excel(xl, 'fontes')
            else:
                return JsonResponse({'error': 'Formato não suportado. Use .csv, .xls ou .xlsx'}, status=400)
            
            # Inserir processos
            for _, row in processes_df.iterrows():
                Process.objects.create(
                    id=row['id'],
                    name=row['nome'],
                    description=row.get('descricao', '')
                )
            
            # Inserir fluxos
            for _, row in flows_df.iterrows():
                Flow.objects.create(
                    from_process_id=row['from_process_id'],
                    to_process_id=row['to_process_id'],
                    amount=row['amount'],
                    unit=row.get('unit', '')
                )
            
            # Inserir fontes emergéticas
            for _, row in sources_df.iterrows():
                EmergySource.objects.create(
                    process_id=row['process_id'],
                    source_name=row['source_name'],
                    transformity=row['transformity'],
                    amount=row['amount'],
                    unit=row.get('unit', '')
                )
            
            return JsonResponse({'message': 'Dados importados com sucesso!', 'processos': len(processes_df)})
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
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
    """Função recursiva para calcular emergia total de um produto"""
    # Buscar fontes emergéticas diretas do processo
    sources = EmergySource.objects.filter(process_id=product_id)
    total = 0
    for source in sources:
        total += source.amount * source.transformity
    
    # Buscar fluxos de entrada (de outros processos para este)
    incoming_flows = Flow.objects.filter(to_process_id=product_id)
    for flow in incoming_flows:
        # Calcular emergia do processo upstream
        upstream_emergy = calculate_emergy(flow.from_process_id)['emergy_sej']
        total += upstream_emergy * flow.amount
    
    return {
        'productId': product_id,
        'emergy_sej': float(total),
        'unit': 'sej'
    }