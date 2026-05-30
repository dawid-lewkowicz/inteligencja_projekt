import streamlit as st
from chatbot import SyllabusChatbot


st.set_page_config(
    page_title="Asystent studenta",
    page_icon="🦉",
    layout="wide" # "centered"
)

st.title("🦉 Inteligentny Asystent Sylabusów")
st.markdown("Zadaj pytanie dotyczące przedmiotów, form zaliczenia lub literatury dotyczące kierunku Informatyka Prakyczna na Uniwersytecie Gdańskim.")
st.divider()

# inicjalizacja bota tylko przy pierwszym wejściu użytkownika na stronę
if "bot" not in st.session_state:
    with st.spinner("Inicjalizacja silnika AI..."):
        try:
            st.session_state.bot = SyllabusChatbot("knowledge_base.json")
        except Exception as e:
            st.error(f"Krytyczny błąd serwera: {e}")
            st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Dzień dobry! O jakim przedmiocie chcesz się dzisiaj dowiedzieć?"}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Napisz swoje pytanie tutaj..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Przygotowuję odpowiedź..."):
            try:
                response = st.session_state.bot.ask(prompt)
                st.markdown(response)
                
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error("Przepraszam, wystąpił problem z połączeniem. Spróbuj ponownie.")