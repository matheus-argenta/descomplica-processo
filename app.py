
import streamlit as st
import pandas as pd
import fitz
import re
import io
from datetime import date, datetime

# --------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# --------------------------------------------------

st.set_page_config(
    page_title="Descomplica Processo",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Descomplica Processo")
st.caption("Assistente demonstrativo para triagem e organização de processos administrativos.")

st.warning(
    "Projeto demonstrativo. Utilize somente documentos fictícios ou "
    "expressamente autorizados. Os arquivos enviados são processados "
    "pelo servidor do aplicativo. Não envie documentos sigilosos ou "
    "que contenham dados pessoais reais."
)

st.info(
    "Esta versão utiliza extração de texto e regras automatizadas. "
    "As informações identificadas devem ser conferidas por uma pessoa."
)

# --------------------------------------------------
# FUNÇÕES DE EXTRAÇÃO
# --------------------------------------------------

def extrair_texto_pdf(arquivo):
    """Extrai o texto de todas as páginas de um PDF."""
    texto = ""

    try:
        documento = fitz.open(stream=arquivo.read(), filetype="pdf")

        for pagina in documento:
            texto += pagina.get_text() + "\n"

        documento.close()

    except Exception:
        return ""

    return texto.strip()


def procurar_campo(texto, padroes):
    """Procura informações identificadas por rótulos conhecidos."""
    for padrao in padroes:
        resultado = re.search(
            padrao,
            texto,
            flags=re.IGNORECASE | re.MULTILINE
        )

        if resultado:
            return resultado.group(1).strip(" \t:;-")

    return "Não identificado no documento"


def identificar_numero(texto):
    padroes = [
        r"(?:N[º°.]?\s*do\s*processo|Processo\s*n[º°.]?)\s*[:\-]?\s*([A-Z0-9./\-]+)",
        r"(?:Protocolo)\s*[:\-]?\s*([A-Z0-9./\-]+)"
    ]

    return procurar_campo(texto, padroes)


def identificar_solicitante(texto):
    padroes = [
        r"(?:Interessado(?:a)?|Requerente|Solicitante)\s*[:\-]\s*([^\n]+)",
        r"(?:Nome do interessado)\s*[:\-]\s*([^\n]+)"
    ]

    return procurar_campo(texto, padroes)


def identificar_assunto(texto):
    padroes = [
        r"(?:Assunto|Objeto|Descrição do pedido)\s*[:\-]\s*([^\n]+)",
        r"(?:Finalidade)\s*[:\-]\s*([^\n]+)"
    ]

    return procurar_campo(texto, padroes)


def identificar_valor(texto):
    padrao = (
        r"(?:Valor solicitado|Valor total|Valor do pedido|Valor estimado)"
        r"\s*[:\-]?\s*(R\$\s?[\d.]+,\d{2}|R\$\s?[\d,]+)"
    )

    return procurar_campo(texto, [padrao])


def identificar_prazo(texto):
    """
    Procura datas próximas de expressões que indiquem prazo.
    Não considera qualquer data do documento como prazo automaticamente.
    """

    padroes = [
        r"(?:prazo final|data limite|vencimento|até o dia|até)\s*[:\-]?\s*"
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
    ]

    resultado = procurar_campo(texto, padroes)

    if resultado == "Não identificado no documento":
        return None

    formatos = ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"]

    for formato in formatos:
        try:
            return datetime.strptime(resultado, formato).date()
        except ValueError:
            continue

    return None


def identificar_pendencias(texto):
    """
    Identifica frases com indicadores comuns de pendência.
    A indicação precisa ser conferida por uma pessoa.
    """

    palavras = [
        "documento pendente",
        "documentação pendente",
        "documento faltante",
        "documentação faltante",
        "necessário apresentar",
        "necessária a apresentação",
        "deverá apresentar",
        "deverá encaminhar",
        "aguardando documentação",
        "falta apresentar"
    ]

    frases = re.split(r"(?<=[.!?])\s+|\n+", texto)
    encontradas = []

    for frase in frases:
        frase_limpa = frase.strip()

        if any(palavra in frase_limpa.lower() for palavra in palavras):
            if frase_limpa and frase_limpa not in encontradas:
                encontradas.append(frase_limpa)

    if encontradas:
        return " | ".join(encontradas[:3])

    return "Nenhuma pendência identificada pelas regras"


def classificar_urgencia(prazo):
    if prazo is None:
        return "Não identificada", None

    dias = (prazo - date.today()).days

    if dias < 0:
        return "🔴 PRAZO VENCIDO", dias
    elif dias <= 2:
        return "🔴 URGENTE", dias
    elif dias <= 7:
        return "🟠 ALTA", dias
    elif dias <= 15:
        return "🟡 MÉDIA", dias
    else:
        return "🟢 BAIXA", dias


def gerar_resumo(dados):
    prazo_texto = (
        dados["Prazo final"].strftime("%d/%m/%Y")
        if dados["Prazo final"]
        else "Não identificado no documento"
    )

    dias_texto = (
        f'{dados["Dias restantes"]} dia(s)'
        if dados["Dias restantes"] is not None
        else "Não calculado"
    )

    return (
        f'**Documento:** {dados["Arquivo"]}\n\n'
        f'**Número/Protocolo:** {dados["Número/Protocolo"]}\n\n'
        f'**Assunto:** {dados["Assunto"]}\n\n'
        f'**Solicitante:** {dados["Solicitante"]}\n\n'
        f'**Valor:** {dados["Valor"]}\n\n'
        f'**Prazo final:** {prazo_texto}\n\n'
        f'**Dias restantes:** {dias_texto}\n\n'
        f'**Urgência sugerida:** {dados["Urgência"]}\n\n'
        f'**Possíveis pendências:** {dados["Possíveis pendências"]}'
    )


def analisar_pdf(arquivo):
    texto = extrair_texto_pdf(arquivo)

    if not texto:
        return {
            "Arquivo": arquivo.name,
            "Status": "Não foi possível extrair texto. PDF pode ser digitalizado.",
            "Número/Protocolo": "Não identificado no documento",
            "Assunto": "Não identificado no documento",
            "Solicitante": "Não identificado no documento",
            "Valor": "Não identificado no documento",
            "Prazo final": None,
            "Dias restantes": None,
            "Urgência": "Não identificada",
            "Possíveis pendências": "Não foi possível analisar o texto",
            "Texto extraído": ""
        }

    prazo = identificar_prazo(texto)
    urgencia, dias = classificar_urgencia(prazo)

    return {
        "Arquivo": arquivo.name,
        "Status": "Texto extraído",
        "Número/Protocolo": identificar_numero(texto),
        "Assunto": identificar_assunto(texto),
        "Solicitante": identificar_solicitante(texto),
        "Valor": identificar_valor(texto),
        "Prazo final": prazo,
        "Dias restantes": dias,
        "Urgência": urgencia,
        "Possíveis pendências": identificar_pendencias(texto),
        "Texto extraído": texto
    }


# --------------------------------------------------
# CONTROLE DOS PROCESSOS
# --------------------------------------------------

if "processos" not in st.session_state:
    st.session_state.processos = []

st.header("1. Importar documentos")

arquivos = st.file_uploader(
    "Selecione um ou mais arquivos PDF",
    type=["pdf"],
    accept_multiple_files=True
)

if st.button("Analisar documentos", type="primary"):
    if not arquivos:
        st.error("Selecione pelo menos um arquivo PDF.")
    else:
        novos_processos = []

        barra = st.progress(0)
        status = st.empty()

        for indice, arquivo in enumerate(arquivos):
            status.write(f"Analisando: {arquivo.name}")

            dados = analisar_pdf(arquivo)
            novos_processos.append(dados)

            barra.progress((indice + 1) / len(arquivos))

        st.session_state.processos.extend(novos_processos)

        status.success(
            f"{len(novos_processos)} documento(s) analisado(s)."
        )

# --------------------------------------------------
# PAINEL DE RESULTADOS
# --------------------------------------------------

processos = st.session_state.processos

if processos:

    st.markdown("---")
    st.header("2. Painel de acompanhamento")

    total = len(processos)

    vencidos = sum(
        1 for p in processos
        if p["Urgência"] == "🔴 PRAZO VENCIDO"
    )

    urgentes = sum(
        1 for p in processos
        if p["Urgência"] == "🔴 URGENTE"
    )

    altos = sum(
        1 for p in processos
        if p["Urgência"] == "🟠 ALTA"
    )

    nao_identificados = sum(
        1 for p in processos
        if p["Urgência"] == "Não identificada"
    )

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Documentos", total)
    col2.metric("Prazos vencidos", vencidos)
    col3.metric("Urgentes", urgentes)
    col4.metric("Alta prioridade", altos)
    col5.metric("Sem prazo identificado", nao_identificados)

    st.markdown("---")
    st.header("3. Lista de processos")

    ordem = {
        "🔴 PRAZO VENCIDO": 0,
        "🔴 URGENTE": 1,
        "🟠 ALTA": 2,
        "🟡 MÉDIA": 3,
        "🟢 BAIXA": 4,
        "Não identificada": 5
    }

    processos_ordenados = sorted(
        processos,
        key=lambda p: ordem.get(p["Urgência"], 6)
    )

    for indice, processo in enumerate(processos_ordenados):
        titulo = (
            f'{processo["Urgência"]} | '
            f'{processo["Arquivo"]}'
        )

        with st.expander(titulo):
            st.markdown(gerar_resumo(processo))

            if processo["Texto extraído"]:
                with st.expander("Consultar texto extraído do PDF"):
                    st.text(processo["Texto extraído"][:12000])

    # --------------------------------------------------
    # EXPORTAÇÃO PARA EXCEL
    # --------------------------------------------------

    st.markdown("---")
    st.header("4. Exportar relatório")

    tabela = pd.DataFrame([
        {
            "Arquivo": p["Arquivo"],
            "Status": p["Status"],
            "Número/Protocolo": p["Número/Protocolo"],
            "Assunto": p["Assunto"],
            "Solicitante": p["Solicitante"],
            "Valor": p["Valor"],
            "Prazo final": (
                p["Prazo final"].strftime("%d/%m/%Y")
                if p["Prazo final"] else ""
            ),
            "Dias restantes": p["Dias restantes"],
            "Urgência": p["Urgência"],
            "Possíveis pendências": p["Possíveis pendências"]
        }
        for p in processos
    ])

    saida = io.BytesIO()

    with pd.ExcelWriter(saida, engine="openpyxl") as escritor:
        tabela.to_excel(
            escritor,
            index=False,
            sheet_name="Processos"
        )

    st.download_button(
        label="📥 Baixar relatório em Excel",
        data=saida.getvalue(),
        file_name="relatorio_descomplica_processo.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    if st.button("Limpar processos da sessão"):
        st.session_state.processos = []
        st.rerun()

else:
    st.info(
        "Nenhum documento analisado ainda. "
        "Envie seus PDFs para começar."
    )

# --------------------------------------------------
# RODAPÉ
# --------------------------------------------------

st.markdown("---")
st.caption(
    "Descomplica Processo | Protótipo demonstrativo | "
    "A classificação é indicativa e exige validação humana."
)
