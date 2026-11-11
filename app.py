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
