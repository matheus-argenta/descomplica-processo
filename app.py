
import streamlit as st
import pandas as pd
import fitz
import re
import io
from datetime import date, datetime

# ==================================================
# 1. CONFIGURAÇÃO
# ==================================================

st.set_page_config(
    page_title="Descomplica Processo",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Descomplica Processo")
st.caption(
    "Assistente demonstrativo para análise, resumo e "
    "priorização de processos administrativos."
)

st.warning(
    "Projeto demonstrativo. Utilize somente documentos fictícios "
    "ou expressamente autorizados. Não envie documentos sigilosos "
    "ou que contenham dados pessoais reais."
)

st.info(
    "Esta versão utiliza extração de texto e regras automatizadas, "
    "não inteligência artificial generativa. Todas as informações "
    "e sugestões precisam de conferência humana."
)


# ==================================================
# 2. EXTRAÇÃO DE TEXTO DOS PDFs
# ==================================================

def extrair_texto_pdf(arquivo):
    texto = ""

    try:
        documento = fitz.open(
            stream=arquivo.getvalue(),
            filetype="pdf"
        )

        for pagina in documento:
            texto += pagina.get_text() + "\n"

        documento.close()

    except Exception:
        return ""

    return texto.strip()


# ==================================================
# 3. IDENTIFICAÇÃO DE INFORMAÇÕES
# ==================================================

NAO_IDENTIFICADO = "Não identificado no documento"


def procurar_campo(texto, padroes):
    for padrao in padroes:
        resultado = re.search(
            padrao,
            texto,
            flags=re.IGNORECASE | re.MULTILINE
        )

        if resultado:
            valor = resultado.group(1).strip(" \t:;-")

            if valor:
                return valor

    return NAO_IDENTIFICADO


def identificar_numero(texto):
    padroes = [
        r"(?:N[º°.]?\s*do\s*processo|Processo\s*n[º°.]?)"
        r"\s*[:\-]?\s*([A-Z0-9./\-]+)",

        r"(?:Protocolo)\s*[:\-]?\s*([A-Z0-9./\-]+)"
    ]

    return procurar_campo(texto, padroes)


def identificar_solicitante(texto):
    padroes = [
        r"(?:Interessado(?:a)?|Requerente|Solicitante)"
        r"\s*[:\-]\s*([^\n]+)",

        r"(?:Nome do interessado)\s*[:\-]\s*([^\n]+)",

        r"(?:Unidade solicitante|Setor solicitante)"
        r"\s*[:\-]\s*([^\n]+)"
    ]

    return procurar_campo(texto, padroes)


def identificar_assunto(texto):
    padroes = [
        r"(?:Assunto|Objeto|Descrição do pedido)"
        r"\s*[:\-]\s*([^\n]+)",

        r"(?:Finalidade)\s*[:\-]\s*([^\n]+)"
    ]

    return procurar_campo(texto, padroes)


def identificar_valor(texto):
    padrao = (
        r"(?:Valor solicitado|Valor total|Valor do pedido|"
        r"Valor estimado|Valor da contratação)"
        r"\s*[:\-]?\s*(R\$\s?[\d.]+,\d{2}|R\$\s?[\d,]+)"
    )

    return procurar_campo(texto, [padrao])


# ==================================================
# 4. IDENTIFICAÇÃO DE PRAZOS
# ==================================================

def identificar_prazo(texto):

    padroes = [
        r"(?:prazo final|data limite|vencimento|até o dia|"
        r"prazo para apresentação|prazo para entrega)"
        r"\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
    ]

    resultado = procurar_campo(texto, padroes)

    if resultado == NAO_IDENTIFICADO:
        return None

    formatos = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d/%m/%y",
        "%d-%m-%y"
    ]

    for formato in formatos:
        try:
            return datetime.strptime(resultado, formato).date()
        except ValueError:
            continue

    return None


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


# ==================================================
# 5. IDENTIFICAÇÃO DE POSSÍVEIS PENDÊNCIAS
# ==================================================

def identificar_pendencias(texto):

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
        "falta apresentar",
        "documento não apresentado"
    ]

    frases = re.split(r"(?<=[.!?])\s+|\n+", texto)

    encontradas = []

    for frase in frases:

        frase_limpa = frase.strip()

        if any(
            palavra in frase_limpa.lower()
            for palavra in palavras
        ):
            if frase_limpa and frase_limpa not in encontradas:
                encontradas.append(frase_limpa)

    if encontradas:
        return encontradas[:3]

    return []


# ==================================================
# 6. GERAÇÃO DO RESUMO EM CINCO TÓPICOS
# ==================================================

def gerar_resumo(dados):

    assunto = dados["Assunto"]
    solicitante = dados["Solicitante"]
    valor = dados["Valor"]
    prazo = dados["Prazo final"]
    pendencias = dados["Pendências"]

    # Tópico 1: objeto do processo

    if assunto != NAO_IDENTIFICADO:
        o_que_e = assunto
    else:
        o_que_e = (
            "O assunto ou objeto do processo não foi "
            "identificado automaticamente."
        )

    # Tópico 2: solicitante

    if solicitante != NAO_IDENTIFICADO:
        quem_pede = solicitante
    else:
        quem_pede = "Solicitante não identificado no documento."

    # Tópico 3: informações identificadas

    informacoes = []

    if valor != NAO_IDENTIFICADO:
        informacoes.append(f"Valor informado: {valor}")

    if dados["Número/Protocolo"] != NAO_IDENTIFICADO:
        informacoes.append(
            f'Número/Protocolo: {dados["Número/Protocolo"]}'
        )

    if informacoes:
        o_que_foi_identificado = "; ".join(informacoes) + "."
    else:
        o_que_foi_identificado = (
            "Não foram identificados automaticamente "
            "outros dados complementares."
        )

    # Tópico 4: pendências

    if pendencias:
        o_que_falta = "Possíveis pendências encontradas: " + " | ".join(
            pendencias
        )
    else:
        o_que_falta = (
            "Nenhuma pendência foi identificada pelas regras "
            "de extração. Isso não significa que a documentação "
            "esteja completa."
        )

    # Tópico 5: prazo e próximo passo

    if prazo:
        prazo_texto = prazo.strftime("%d/%m/%Y")
        dias = dados["Dias restantes"]

        if dias < 0:
            situacao = f"Prazo vencido há {abs(dias)} dia(s)."
        elif dias == 0:
            situacao = "O prazo termina hoje."
        else:
            situacao = f"Restam {dias} dia(s) para o prazo."

        prazo_resumo = (
            f"Prazo final: {prazo_texto}. {situacao}"
        )

    else:
        prazo_resumo = (
            "Prazo final não identificado no documento."
        )

    if pendencias:
        proximo_passo = (
            "Sugestão: conferir as possíveis pendências "
            "e verificar a necessidade de complementação documental."
        )
    elif prazo and dados["Dias restantes"] <= 2:
        proximo_passo = (
            "Sugestão: priorizar a conferência do prazo e "
            "encaminhar o processo ao setor responsável."
        )
    else:
        proximo_passo = (
            "Sugestão: conferir as informações e encaminhar "
            "o processo para análise do setor responsável."
        )

    return {
        "O que é": o_que_e,
        "Quem solicita": quem_pede,
        "Informações identificadas": o_que_foi_identificado,
        "Pendências": o_que_falta,
        "Prazo e próximo passo": prazo_resumo + " " + proximo_passo
    }


# ==================================================
# 7. ANÁLISE COMPLETA DE CADA DOCUMENTO
# ==================================================

def analisar_pdf(arquivo):

    texto = extrair_texto_pdf(arquivo)

    if not texto:

        dados = {
            "Arquivo": arquivo.name,
            "Status": (
                "Não foi possível extrair texto. "
                "O PDF pode ser digitalizado."
            ),
            "Número/Protocolo": NAO_IDENTIFICADO,
            "Assunto": NAO_IDENTIFICADO,
            "Solicitante": NAO_IDENTIFICADO,
            "Valor": NAO_IDENTIFICADO,
            "Prazo final": None,
            "Dias restantes": None,
            "Urgência": "Não identificada",
            "Pendências": [],
            "Texto extraído": ""
        }

        dados["Resumo"] = gerar_resumo(dados)

        return dados

    prazo = identificar_prazo(texto)
    urgencia, dias = classificar_urgencia(prazo)

    dados = {
        "Arquivo": arquivo.name,
        "Status": "Texto extraído com sucesso",
        "Número/Protocolo": identificar_numero(texto),
        "Assunto": identificar_assunto(texto),
        "Solicitante": identificar_solicitante(texto),
        "Valor": identificar_valor(texto),
        "Prazo final": prazo,
        "Dias restantes": dias,
        "Urgência": urgencia,
        "Pendências": identificar_pendencias(texto),
        "Texto extraído": texto
    }

    dados["Resumo"] = gerar_resumo(dados)

    return dados


# ==================================================
# 8. ARMAZENAMENTO NA SESSÃO
# ==================================================

if "processos" not in st.session_state:
    st.session_state.processos = []


# ==================================================
# 9. IMPORTAÇÃO DOS DOCUMENTOS
# ==================================================

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
            f"{len(novos_processos)} documento(s) analisado(s)!"
        )


# ==================================================
# 10. PAINEL DE ACOMPANHAMENTO
# ==================================================

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

    sem_prazo = sum(
        1 for p in processos
        if p["Prazo final"] is None
    )

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Documentos", total)
    col2.metric("Prazos vencidos", vencidos)
    col3.metric("Urgentes", urgentes)
    col4.metric("Prioridade alta", altos)
    col5.metric("Sem prazo", sem_prazo)


    # ==================================================
    # 11. LISTA DE PROCESSOS
    # ==================================================

    st.markdown("---")
    st.header("3. Processos analisados")

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
        key=lambda p: (
            ordem.get(p["Urgência"], 6),
            p["Dias restantes"]
            if p["Dias restantes"] is not None
            else 999999
        )
    )

    for indice, processo in enumerate(processos_ordenados):

        titulo = (
            f'{processo["Urgência"]} | '
            f'{processo["Arquivo"]}'
        )

        with st.expander(titulo):

            # RESUMO DO PROCESSO

            st.subheader("📋 Resumo do processo")

            st.markdown(
                f'**1. O que é:** {processo["Resumo"]["O que é"]}'
            )

            st.markdown(
                f'**2. Quem solicita:** '
                f'{processo["Resumo"]["Quem solicita"]}'
            )

            st.markdown(
                f'**3. Informações identificadas:** '
                f'{processo["Resumo"]["Informações identificadas"]}'
            )

            st.markdown(
                f'**4. O que falta:** '
                f'{processo["Resumo"]["Pendências"]}'
            )

            st.markdown(
                f'**5. Prazo e próximo passo:** '
                f'{processo["Resumo"]["Prazo e próximo passo"]}'
            )

            # DADOS DETALHADOS

            st.markdown("---")
            st.subheader("🔎 Dados detalhados")

            c1, c2 = st.columns(2)

            with c1:
                st.write(
                    "**Número/Protocolo:**",
                    processo["Número/Protocolo"]
                )

                st.write(
                    "**Solicitante:**",
                    processo["Solicitante"]
                )

                st.write(
                    "**Assunto:**",
                    processo["Assunto"]
                )

            with c2:
                st.write(
                    "**Valor:**",
                    processo["Valor"]
                )

                st.write(
                    "**Prazo final:**",
                    processo["Prazo final"].strftime("%d/%m/%Y")
                    if processo["Prazo final"]
                    else NAO_IDENTIFICADO
                )

                st.write(
                    "**Dias restantes:**",
                    processo["Dias restantes"]
                    if processo["Dias restantes"] is not None
                    else "Não calculado"
                )

            st.write("**Status da extração:**", processo["Status"])

            if processo["Texto extraído"]:

                with st.expander("Consultar texto original extraído"):

                    st.text(
                        processo["Texto extraído"][:15000]
                    )


    # ==================================================
    # 12. EXPORTAÇÃO PARA EXCEL
    # ==================================================

    st.markdown("---")
    st.header("4. Exportar relatório")

    linhas_excel = []

    for p in processos:

        linhas_excel.append({
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
            "Resumo - O que é": p["Resumo"]["O que é"],
            "Resumo - Quem solicita": p["Resumo"]["Quem solicita"],
            "Resumo - Informações": p["Resumo"]["Informações identificadas"],
            "Resumo - Pendências": p["Resumo"]["Pendências"],
            "Resumo - Prazo e próximo passo": p["Resumo"]["Prazo e próximo passo"]
        })

    tabela = pd.DataFrame(linhas_excel)

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
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )


    # ==================================================
    # 13. LIMPAR A SESSÃO
    # ==================================================

    if st.button("Limpar processos da sessão"):

        st.session_state.processos = []
        st.rerun()

else:

    st.info(
        "Nenhum documento analisado ainda. "
        "Envie seus PDFs para começar."
    )


# ==================================================
# 14. RODAPÉ
# ==================================================

st.markdown("---")

st.caption(
    "Descomplica Processo | Protótipo demonstrativo | "
    "Resumos e classificações automatizados por regras. "
    "A conferência humana é indispensável."
)
