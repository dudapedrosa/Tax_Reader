import streamlit as st
import google.generativeai as genai
import pandas as pd
import os
import json
import re
from datetime import datetime
import time
from io import BytesIO
import base64

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Tax Reader - Pague Menos",
    page_icon="",
    layout="wide"
)

# --- FUNÇÃO PARA CARREGAR IMAGEM LOCAL NO HTML (BASE64) ---
def get_image_base64(path):
    """Lê um arquivo de imagem e converte para string Base64."""
    try:
        with open(path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        # Detecta extensão simples
        if path.endswith(".png"): mime = "image/png"
        elif path.endswith(".jpg") or path.endswith(".jpeg"): mime = "image/jpeg"
        else: mime = "image/png"
        return f"data:{mime};base64,{encoded_string}"
    except Exception as e:
        return None # Retorna None se não achar a imagem

# --- DEFINIÇÃO DOS CAMINHOS DAS IMAGENS ---
# Certifique-se que a pasta 'img' existe ao lado deste arquivo
IMG_LOGO = os.path.join("img", "logo_pgmn.png")
IMG_ICON = os.path.join("img", "logo_pgmn.png") # Ícone de pagamento opcional

# --- CSS PERSONALIZADO (BRANDING PAGUE MENOS) ---
st.markdown("""
    <style>
    /* Cores Pague Menos */
    :root {
        --pm-blue: #005CA9;
        --pm-red: #E30613;
        --pm-bg: #F4F6F9;
        --pm-text: #333333;
    }
    
    .stApp {
        background-color: var(--pm-bg);
    }
    
    /* Cabeçalho Personalizado */
    .header-container {
        display: flex;
        align-items: center;
        padding-bottom: 15px;
        border-bottom: 3px solid var(--pm-red);
        margin-bottom: 25px;
    }
    
    .header-logo {
        height: 65px; /* Tamanho da logo */
        margin-right: 20px;
    }
    
    .header-title {
        color: var(--pm-blue);
        font-family: 'Helvetica', sans-serif;
        font-weight: 700;
        font-size: 2.2rem;
        margin: 0;
    }
    
    /* Botões */
    .stButton>button {
        background-color: var(--pm-blue);
        color: white;
        border-radius: 8px;
        border: none;
        padding: 12px 28px;
        font-weight: bold;
        font-size: 16px;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: var(--pm-red);
        color: white;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Cards de Métricas */
    div[data-testid="stMetric"] {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border-left: 5px solid var(--pm-blue);
    }
    </style>
""", unsafe_allow_html=True)

# --- RENDERIZAÇÃO DO CABEÇALHO ---
logo_b64 = get_image_base64(IMG_LOGO)

if logo_b64:
    # Se a imagem existe, usa ela
    st.markdown(f"""
        <div class="header-container">
            <img src="{logo_b64}" class="header-logo" alt="Logo Pague Menos">
            <h1 class="header-title">Tax Reader - Inteligência de Tributos Municipais </h1>
        </div>
    """, unsafe_allow_html=True)
else:
    # Fallback se a imagem não for encontrada
    st.markdown('<div class="header-container"><h1 class="header-title"> Robô de Lançamento de Guias</h1></div>', unsafe_allow_html=True)

# --- SIDEBAR (CONFIGURAÇÕES) ---
with st.sidebar:
    # Tenta mostrar o ícone de pagamento ou a logo novamente na sidebar
    #if os.path.exists():
        #t.image(IMG_ICON, width=100)
    #elif os.path.exists(IMG_LOGO):
        #st.image(IMG_LOGO, width=180)
    
    st.header("")
    api_key = st.text_input("Chave de Requisição - API", value="", type="password", help="Insira sua chave AIza...")
    uploaded_ref = st.file_uploader("📂 Base de Dados (.xlsx)", type=["xlsx"])
    
    #st.info("ℹ️ **Ajuda:**\nO arquivo deve conter as colunas 'Empresa', 'Centro', 'Centro de Custo' e as Receitas.")

# --- LÓGICA DE NEGÓCIO ---
def aplicar_regras(dados, nome_arq, df_ref):
    comentario = nome_arq.replace(".pdf", "").replace(".PDF", "")
    print(comentario)

    # 1. Identificar Loja
    match_loja = re.search(r'LJ\s*(\d+)', comentario, re.IGNORECASE)
    num_int = int(match_loja.group(1)) if match_loja else 0

    # 2. Identificar Data/Competência
    match_data = re.search(r'(\d{2})\.?(\d{4})', comentario)
    mes = int(match_data.group(1)) if match_data else 0
    ano = int(match_data.group(2)) if match_data else 0
    competencia = (ano * 100) + mes 

    # Colunas Básicas
    dados['Loja'] = f"LOJA{num_int}"
    dados['Comentário'] = comentario
    dados['NF'] = ""
    
    # Regra de Empresa
    empresa = 1000 if 1 <= num_int <= 1583 else 2000 if 7001 <= num_int <= 7575 else None

    try:
        busca = df_ref[(df_ref['Empresa'] == empresa) & (df_ref['Centro'] == num_int)]
        
        #PARA EMPRESA 1000
        if not busca.empty and empresa == 1000:
            linha = busca.iloc[0]
            dados['Centro de custo'] = linha['Centro de Custo']

            # Lógica de Receita
            # Verifica se a palavra 'proprio' (com ou sem acento) está no comentário
            
            #PARA A EMPRESA 1000
            if "propri" in comentario.lower():
                dados['Código de Receita (Interno)'] = linha.get('Receita 2', '')
            elif competencia >= 202501:   
                dados['Código de Receita (Interno)'] = linha.get('Receita 3', '')
            elif 202001 <= competencia <= 202412:
                dados['Código de Receita (Interno)'] = linha.get('Receita 1', '')
            else:
                dados['Código de Receita (Interno)'] = "DATA FORA DO RANGE"

            #PARA EMPRESA 2000
        elif not busca.empty and empresa == 2000:
            linha = busca.iloc[0]
            dados['Centro de custo'] =linha['Centro de Custo']
            
            if "propi" in comentario.lower():
                dados['Código de Receita (Interno)'] = linha.get('Receita 2', '')
            elif 202001 <= competencia >= 202501:
                dados['Código de Receita (Interno)'] = linha.get('Receita 3', '')
            else:
                dados['Código de Receita (Interno)'] = "DATA FORA DO RANGE"

        else:
            dados['Centro de custo'] = "NÃO ENCONTRADO"
            dados['Código de Receita (Interno)'] = "VERIFICAR"
    except Exception as e:
        dados['Centro de custo'] = f"ERRO: {e}"
        dados['Código de Receita (Interno)'] = "ERRO"
    
    return dados

def processar_arquivos(uploaded_files, df_ref, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('models/gemini-3-flash-preview')
    
    data_hoje = datetime.now().strftime('%d/%m/%Y')
    
    PROMPT_IA = f"""
    Você é um Analista Tributário sênior. Sua tarefa é extrair dados de guias de pagamento de impostos.
    CONSIDERAÇÕES IMPORTANTES:
    1. DATA DE VENCIMENTO: Extraia a data limite para pagamento sem juros. Se houver múltiplas datas, escolha a data de vencimento final. Hoje é {data_hoje}.
    2. VALORES: Extraia os valores brutos. Se não encontrar algum campo, retorne 0.0.
    3. CÓDIGO DE BARRAS: Extraia apenas os números, sem espaços ou pontos.
    4. Não calcule nenhum valor, extrair somente os campos solicitados.
    5. Se o documento tiver mais de uma página, considerar só uma ocorrência dos campos solicitados.

    Retorne EXCLUSIVAMENTE um JSON com este formato:
    {{
      "Valor do Tributo": 00,
      "Valor Atualização Monetária": 00,
      "Valor Juros/Encargos/Mora": 00,
      "Valor Multa": 00,
      "Valor Outros": 00,
      "Valor do Acréscimo": 00,
      "Valor do Desconto/Abatimento": 00,
      "Valor do Pagamento": 00,
      "Data de Vencimento": "DD/MM/AAAA",
      "Código Barras": "apenas numeros, sem espaços"
    }}
    """
    
    resultados = []
    progresso = st.progress(0)
    status_text = st.empty()
    total = len(uploaded_files)
    
    for i, uploaded_file in enumerate(uploaded_files):
        status_text.text(f"🔍 Processando {i+1}/{total}: {uploaded_file.name}...")
        try:
            bytes_data = uploaded_file.getvalue()
            pdf_parts = [{"mime_type": "application/pdf", "data": bytes_data}]
            
            res = model.generate_content([PROMPT_IA, pdf_parts[0]])
            
            json_str = res.text.replace('```json', '').replace('```', '').strip()
            dados_ia = json.loads(json_str)
            
            dados_finais = aplicar_regras(dados_ia, uploaded_file.name, df_ref)
            resultados.append(dados_finais)
            
        except Exception as e:
            st.error(f"Erro em {uploaded_file.name}: {e}")
        
        progresso.progress((i + 1) / total)
        time.sleep(1) 
        
    status_text.text("✅ Processamento Concluído!")
    
    if resultados:
        df_final = pd.DataFrame(resultados)
        
        ordem_colunas = [
            "Loja", "Centro de custo", "Código de Receita (Interno)", 
            "Valor do Tributo", "Valor Atualização Monetária", 
            "Valor Juros/Encargos/Mora", "Valor Multa", "Valor Outros", "Valor do Acréscimo",
            "Valor do Desconto/Abatimento", "Valor do Pagamento", 
            "Data de Vencimento", "Código Barras", "Comentário", "NF"
        ]
        
        for col in ordem_colunas:
            if col not in df_final.columns:
                df_final[col] = ""
        
        return df_final[ordem_colunas]
    
    return pd.DataFrame()

# --- INTERFACE PRINCIPAL ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("1. Upload das Guias (PDF)")
    uploaded_pdfs = st.file_uploader("Arraste os arquivos PDF aqui", type=["pdf"], accept_multiple_files=True)

with col2:
    st.subheader("Resumo")
    if uploaded_pdfs:
        st.metric(label="Arquivos na Fila", value=len(uploaded_pdfs))
    else:
        st.info("Aguardando arquivos...")

if st.button("🚀 Iniciar Processamento"):
    if not api_key:
        st.warning("⚠️ Insira a Chave API no menu lateral.")
    elif uploaded_ref is None:
        st.warning("⚠️ Carregue a Base de Dados no menu lateral.")
    elif not uploaded_pdfs:
        st.warning("⚠️ Selecione pelo menos um PDF.")
    else:
        with st.spinner('O Robô está trabalhando...'):
            try:
                df_ref_loaded = pd.read_excel(uploaded_ref)
                df_ref_loaded['Empresa'] = pd.to_numeric(df_ref_loaded['Empresa'], errors='coerce')
                df_ref_loaded['Centro'] = pd.to_numeric(df_ref_loaded['Centro'], errors='coerce')
                
                df_resultado = processar_arquivos(uploaded_pdfs, df_ref_loaded, api_key)
                
                if not df_resultado.empty:
                    st.success("Processamento finalizado com sucesso!")
                    
                    st.markdown("### 📊 Prévia dos Dados")
                    st.dataframe(df_resultado.head(), use_container_width=True)
                    
                    # Buffer para Download
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df_resultado.to_excel(writer, index=False)
                    
                    st.download_button(
                        label="📥 Baixar Planilha Final (.xlxs)",
                        data=buffer.getvalue(),
                        file_name=f"Lancamento_Guias_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.ms-excel"
                    )
            except Exception as e:
                st.error(f"Erro Crítico: {e}")