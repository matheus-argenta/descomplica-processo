import streamlit as st

st.set_page_config(page_title="Descomplica Processo", page_icon="📄")
st.title("📄 Descomplica Processo")
st.warning("⚠️ Projeto demonstrativo - Todos os dados aqui são fictícios. Nenhum processo real foi utilizado, em respeito à LGPD.")
st.write("IA que resume processos públicos em 5 linhas.")

processo = st.text_area("Cole aqui o texto do processo (fictício):", height=150)

if st.button("Resumir processo"):
    if processo:
        st.success("Resumo gerado:")
        st.write("1. **O que é:** Solicitação de análise administrativa.")
        st.write("2. **Quem pede:** Servidor fictício.")
        st.write("3. **O que falta:** Documento de identificação.")
        st.write("4. **Próximo passo:** Encaminhar para análise.")
        st.write("5. **Prazo estimado:** 5 dias úteis.")
    else:
        st.error("Cole um texto primeiro.")

import streamlit as st
from datetime import date

st.markdown("---")
st.header("📋 Classificar Processos por Urgência")

# Guarda os processos na memória
if "processos" not in st.session_state:
    st.session_state.processos = []

# Formulário para cadastrar
with st.form("novo_processo"):
    nome = st.text_input("Nome do processo")
    tipo = st.selectbox("Tipo", ["Cível", "Trabalhista", "Penal", "Previdenciário", "Outro"])
    prazo = st.date_input("Prazo final", value=date.today())
    enviar = st.form_submit_button("Adicionar processo")

    if enviar and nome:
        dias_restantes = (prazo - date.today()).days

        # Classificação automática
        if dias_restantes <= 2:
            urgencia = "🔴 URGENTE"
            nivel = 0
        elif dias_restantes <= 7:
            urgencia = "🟠 ALTA"
            nivel = 1
        elif dias_restantes <= 15:
            urgencia = "🟡 MÉDIA"
            nivel = 2
        else:
            urgencia = "🟢 BAIXA"
            nivel = 3

        st.session_state.processos.append({
            "Processo": nome,
            "Tipo": tipo,
            "Prazo": prazo.strftime("%d/%m/%Y"),
            "Dias restantes": dias_restantes,
            "Urgência": urgencia,
            "nivel": nivel
        })
        st.success("Processo adicionado!")

# Mostra a lista já ordenada do mais urgente pro menos urgente
if st.session_state.processos:
    st.subheader("Lista ordenada por urgência")
    
    # Ordena por nível
    lista_ordenada = sorted(st.session_state.processos, key=lambda x: x["nivel"])
    
    for p in lista_ordenada:
        st.write(f"{p['Urgência']} | **{p['Processo']}** - {p['Tipo']} - Prazo: {p['Prazo']} ({p['Dias restantes']} dias)")
else:
    st.info("Nenhum processo cadastrado ainda. Cadastra o primeiro ali em cima!")
