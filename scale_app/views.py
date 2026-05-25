import os
import io
import json
import base64

import pandas as pd
import numpy as np

import matplotlib
matplotlib.use('Agg')  # Backend sem display gráfico — DEVE vir antes de importar pyplot
import matplotlib.pyplot as plt

from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt

from .models import Inventory, Process, Flow, EmergySource
from .utils.emergy_calculator import calculate_emergy, calculate_emergy_with_report


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
# LISTAR INVENTÁRIOS
# ============================================================
def list_inventories(request):
    """Retorna JSON com todos os inventários salvos, do mais recente ao mais antigo."""
    inventories = Inventory.objects.order_by('-created_at').values('id', 'name', 'created_at')
    data = []
    for inv in inventories:
        data.append({
            'id': inv['id'],
            'name': inv['name'],
            'created_at': inv['created_at'].strftime('%d/%m/%Y %H:%M'),
        })
    return JsonResponse(data, safe=False)


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

    try:

        # ====================================================
        # CRIAR INVENTÁRIO (em vez de deletar dados globais)
        # ====================================================
        inventory = Inventory.objects.create(name=uploaded_file.name)

        # ====================================================
        # LEITURA DO ARQUIVO
        # ====================================================
        if extension == 'csv':
            df = pd.read_csv(uploaded_file)

        elif extension in ['xls', 'xlsx']:
            df = pd.read_excel(uploaded_file)

        else:
            inventory.delete()
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
                inventory.delete()
                return JsonResponse({
                    'error': f'Coluna obrigatória não encontrada: {col}'
                }, status=400)

        # ====================================================
        # MAPEAR CATEGORIAS DE FONTES (se existir coluna)
        # ====================================================
        category_map = {
            'renovável': 'R', 'renovavel': 'R', 'renewable': 'R', 'r': 'R',
            'não renovável': 'N', 'nao renovavel': 'N', 'non-renewable': 'N',
            'non renewable': 'N', 'n': 'N',
            'materiais': 'M', 'materials': 'M', 'material': 'M', 'm': 'M',
        }
        has_category = 'categoria_fonte' in df.columns

        # ====================================================
        # CRIAR PROCESSOS
        # ====================================================
        processos_unicos = (
            df[['processo_destino_id', 'nome_processo_destino']]
            .dropna()
            .drop_duplicates()
        )

        # Mapa de ID da planilha → ID real do banco (auto-gerado)
        process_id_map = {}

        for _, row in processos_unicos.iterrows():

            old_id = int(row['processo_destino_id'])

            process = Process.objects.create(
                inventory=inventory,
                name=str(row['nome_processo_destino']).strip(),
                description=''
            )

            process_id_map[old_id] = process.id

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
                old_id = int(row['processo_destino_id'])

                mapa_saidas[insumo] = process_id_map.get(old_id, old_id)

        # ====================================================
        # PROCESSAR LINHAS
        # ====================================================
        for _, row in df.iterrows():

            old_to_id = int(row['processo_destino_id'])
            to_process_id = process_id_map.get(old_to_id, old_to_id)

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

            # Determinar categoria da fonte
            category = 'U'
            if has_category:
                cat_raw = str(row.get('categoria_fonte', '')).strip().lower()
                category = category_map.get(cat_raw, 'U')

            # ================================================
            # É FONTE EXTERNA
            # ================================================
            if uev > 0:

                EmergySource.objects.create(
                    inventory=inventory,
                    process_id=to_process_id,
                    source_name=insumo,
                    category=category,
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
                        inventory=inventory,
                        from_process_id=from_process_id,
                        to_process_id=to_process_id,
                        amount=quantidade,
                        unit=unidade
                    )

                else:
                    # fallback seguro
                    EmergySource.objects.create(
                        inventory=inventory,
                        process_id=to_process_id,
                        source_name=insumo,
                        category=category,
                        transformity=0.0,
                        amount=quantidade,
                        unit=unidade
                    )

        return JsonResponse({
            'message': 'Importação concluída com sucesso!',
            'inventory_id': inventory.id,
            'inventory_name': inventory.name,
            'processos': Process.objects.filter(inventory=inventory).count(),
            'flows': Flow.objects.filter(inventory=inventory).count(),
            'sources': EmergySource.objects.filter(inventory=inventory).count()
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
        return JsonResponse({'error': 'Método não permitido'}, status=405)

    try:
        data = json.loads(request.body)
        product_id = data.get('productId')
        inventory_id = data.get('inventoryId')  # opcional

        if not product_id:
            return JsonResponse({'error': 'productId é obrigatório'}, status=400)

        # Chama a função correta importada do emergy_calculator.py
        result = calculate_emergy_with_report(
            int(product_id),
            inventory_id=int(inventory_id) if inventory_id else None
        )

        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================
# DASHBOARD API — Gráficos em Base64
# ============================================================
def dashboard_api(request, inventory_id):
    """
    Calcula a emergia total dos produtos de um inventário e gera
    3 gráficos com matplotlib, retornando-os como strings base64.
    """
    try:
        inventory = Inventory.objects.get(id=inventory_id)
    except Inventory.DoesNotExist:
        return JsonResponse({'error': 'Inventário não encontrado'}, status=404)

    # Buscar dados do inventário
    processes = Process.objects.filter(inventory=inventory)
    sources = EmergySource.objects.filter(inventory=inventory)

    if not processes.exists():
        return JsonResponse({
            'error': 'Nenhum processo encontrado neste inventário'
        }, status=404)

    # Estilo global para os gráficos
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Segoe UI', 'Helvetica', 'Arial', 'sans-serif'],
        'font.size': 14,
        'axes.titlesize': 18,
        'axes.labelsize': 14,
        'xtick.labelsize': 12,
        'ytick.labelsize': 12,
        'text.color': '#121C2A',
        'axes.labelcolor': '#121C2A',
        'figure.facecolor': 'white',
        'axes.facecolor': 'white',
    })

    # ========================================================
    # 2) GRÁFICO DE BARRAS — Emergia total por Processo (Top 10)
    # ========================================================
    process_emergy = {}
    for proc in processes:
        try:
            total = calculate_emergy(proc.id, inventory_id=inventory.id)
            process_emergy[proc.name] = total
        except Exception:
            process_emergy[proc.name] = 0

    # Ordenar por valor e pegar os top 10
    sorted_procs = sorted(
        process_emergy.items(), key=lambda x: x[1], reverse=True
    )[:10]
    bar_names = [p[0] for p in sorted_procs]
    bar_values = [p[1] for p in sorted_procs]

    fig2, ax2 = plt.subplots(figsize=(8, 5))

    if bar_values:
        # Criar cores em gradiente verde (escuro → claro)
        n = len(bar_names)
        bar_colors = []
        for i in range(n):
            ratio = i / max(n - 1, 1)
            r = int(0x00 + (0xb1 - 0x00) * ratio)
            g = int(0x6b + (0xf2 - 0x6b) * ratio)
            b = int(0x2c + (0xbe - 0x2c) * ratio)
            bar_colors.append(f'#{r:02x}{g:02x}{b:02x}')

        bars = ax2.barh(
            range(len(bar_names)), bar_values,
            color=bar_colors, edgecolor='white', linewidth=0.8,
            height=0.65
        )
        ax2.set_yticks(range(len(bar_names)))
        ax2.set_yticklabels(bar_names, fontsize=11, color='#121C2A')
        ax2.invert_yaxis()
        ax2.set_xlabel('Emergia Total (sej)', fontsize=13, color='#3e4a3d')
        ax2.tick_params(axis='x', colors='#6e7b6c', labelsize=10)

        # Adicionar valores nas barras
        for bar_rect, val in zip(bars, bar_values):
            width = bar_rect.get_width()
            if val > 0:
                label = f'{val:.2e}'
                ax2.text(
                    width * 1.02, bar_rect.get_y() + bar_rect.get_height() / 2,
                    label, va='center', fontsize=9, color='#3e4a3d'
                )
    else:
        ax2.text(
            0.5, 0.5, 'Sem dados',
            ha='center', va='center', transform=ax2.transAxes,
            color='#9CA3AF', fontsize=14
        )

    ax2.set_title(
        'Emergia por Processo (Top 10)',
        fontsize=18, fontweight='bold', color='#121C2A', pad=15
    )
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.spines['left'].set_color('#bdcaba')
    ax2.spines['bottom'].set_color('#bdcaba')
    fig2.tight_layout()

    buf2 = io.BytesIO()
    fig2.savefig(buf2, format='png', dpi=200, transparent=False, bbox_inches='tight', pad_inches=0.1)
    buf2.seek(0)
    bar_b64 = base64.b64encode(buf2.getvalue()).decode('utf-8')
    plt.close(fig2)

    # ========================================================
    # 3) GRÁFICO DE LINHAS — Valores de UEV (Transformidade)
    # ========================================================
    uev_data = []
    for src in sources:
        if src.transformity and src.transformity > 0:
            uev_data.append({
                'name': src.source_name,
                'uev': src.transformity,
            })

    uev_data.sort(key=lambda x: x['uev'])

    fig3, ax3 = plt.subplots(figsize=(8, 5))

    if uev_data:
        uev_names = [d['name'] for d in uev_data]
        uev_values = [d['uev'] for d in uev_data]
        x_pos = range(len(uev_names))

        ax3.plot(
            x_pos, uev_values,
            color='#006b2c', linewidth=2.5,
            marker='o', markersize=9,
            markerfacecolor='#16A34A', markeredgecolor='#006b2c',
            markeredgewidth=1.5, zorder=3
        )
        ax3.fill_between(
            x_pos, uev_values,
            alpha=0.12, color='#16A34A'
        )

        ax3.set_xticks(x_pos)
        ax3.set_xticklabels(
            uev_names, rotation=45, ha='right', fontsize=11, color='#121C2A'
        )
        ax3.set_ylabel('UEV (sej/unidade)', fontsize=13, color='#3e4a3d')
        ax3.tick_params(axis='y', colors='#6e7b6c', labelsize=10)
        ax3.grid(axis='y', linestyle='--', alpha=0.3, color='#bdcaba')
    else:
        ax3.text(
            0.5, 0.5, 'Sem dados de UEV',
            ha='center', va='center', transform=ax3.transAxes,
            color='#9CA3AF', fontsize=14
        )

    ax3.set_title(
        'Valores de UEV (Transformidade)',
        fontsize=18, fontweight='bold', color='#121C2A', pad=15
    )
    ax3.spines['top'].set_visible(False)
    ax3.spines['right'].set_visible(False)
    ax3.spines['left'].set_color('#bdcaba')
    ax3.spines['bottom'].set_color('#bdcaba')
    fig3.tight_layout()

    buf3 = io.BytesIO()
    fig3.savefig(buf3, format='png', dpi=200, transparent=False, bbox_inches='tight', pad_inches=0.1)
    buf3.seek(0)
    line_b64 = base64.b64encode(buf3.getvalue()).decode('utf-8')
    plt.close(fig3)

    # ========================================================
    # 4) CÁLCULO DOS INDICADORES REAIS (EYR e Renovabilidade)
    # ========================================================
    cat_data = {'R': 0, 'N': 0, 'M': 0, 'U': 0}
    for src in sources:
        emergy_sej = (src.amount or 0) * (src.transformity or 0)
        cat = src.category or 'U'
        cat_data[cat] = cat_data.get(cat, 0) + emergy_sej

    R = cat_data.get('R', 0)
    N = cat_data.get('N', 0)
    F = cat_data.get('M', 0) + cat_data.get('U', 0)
    total_emergy = R + N + F

    renovability = (R / total_emergy * 100) if total_emergy > 0 else 0
    eyr = (total_emergy / F) if F > 0 else (total_emergy if total_emergy > 0 else 0)

    # ========================================================
    # RETORNO JSON COM BASE64 E INDICADORES
    # ========================================================
    return JsonResponse({
        'inventory_name': inventory.name,
        'bar_chart': f'data:image/png;base64,{bar_b64}',
        'line_chart': f'data:image/png;base64,{line_b64}',
        'ren_value': f"{renovability:.2f}",
        'eyr_value': f"{eyr:.2f}",
    })


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