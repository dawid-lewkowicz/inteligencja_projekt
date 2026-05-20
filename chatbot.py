import os
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("Błąd: Brak klucza w pliku .env!")

class SyllabusChatbot:
    def __init__(self, database_path="knowledge_base.json"):
        # temperature=0 powoduje brak halucynacji
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.database = self._load_database(database_path)
        self.course_names = [course["nazwa"] for course in self.database]
        self.chat_history = []

    def _load_database(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _identify_course(self, user_query: str) -> str:
        history_str = ""
        for msg in self.chat_history: 
            history_str += f"{msg['role']}: {msg['content']}\n"

        system_prompt = (
            "Jesteś TYLKO I WYŁĄCZNIE precyzyjnym routerem. Twoim jedynym zadaniem jest wyciągnięcie nazwy przedmiotu z zapytania.\n"
            "MASZ ABSOLUTNY ZAKAZ ODPOWIADANIA NA PYTANIA STUDENTA. Nie wolno Ci pisać, kto prowadzi przedmiot, ani ile ma ECTS.\n\n"
            f"Baza przedmiotów: {', '.join(self.course_names)}\n\n"
            "ZASADY (ZWRÓĆ TYLKO JEDNĄ Z PONIŻSZYCH WARTOŚCI, NIC WIĘCEJ):\n"
            "1. GLOBALNE - pytania o wszystkie przedmioty.\n"
            "2. WIELE - pytania ogólne (np. samo 'programowanie').\n"
            "3. [PEŁNA NAZWA Z BAZY] - Jeśli wiesz o jaki przedmiot chodzi. Zwróć SAMĄ NAZWĘ, nic więcej. UWAGA: Jeśli student używa zaimków (np. 'ten przedmiot', 'a kto go prowadzi?'), MUSISZ spojrzeć w Historię Rozmowy i wywnioskować, o czym rozmawialiście sekundę temu, a następnie zwrócić pełną nazwę tego przedmiotu.\n"
            "4. BRAK - Tylko gdy pytanie nie dotyczy nauki (np. 'cześć').\n\n"
            "Historia rozmowy:\n"
            f"{history_str}\n"
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "Najnowsze pytanie: {query}")
        ])
        
        chain = prompt | self.llm
        response = chain.invoke({"query": user_query})
        return response.content.strip()

    def ask(self, user_query: str) -> str:
        raw_match = self._identify_course(user_query).strip().replace(".", "")
        matched_course = raw_match.upper() if raw_match.upper() in ["WIELE", "GLOBALNE", "BRAK"] else raw_match
        
        print(f"\n[DEBUG ROUTERA] Zidentyfikowano jako: {matched_course}")
        
        if matched_course == "WIELE":
            output_text = (
                "Twoje zapytanie pasuje do kilku przedmiotów (mamy np. Wstęp do programowania, "
                "Języki programowania I oraz Języki programowania II). Sprecyzuj, o który dokładnie Ci chodzi."
            )
            self._update_memory(user_query, output_text)
            return output_text
            
        elif matched_course == "GLOBALNE":
            summary = [{"nazwa": c["nazwa"], "ects": c["ects"]} for c in self.database]
            context_str = "Lista wszystkich dostępnych przedmiotów i ich ECTS:\n" + json.dumps(summary, indent=2, ensure_ascii=False)
            
        elif matched_course == "BRAK":
            context_str = "Brak szczegółowych danych. Poproś studenta o sprecyzowanie pytania lub podanie nazwy przedmiotu."
            
        else:
            context = None
            normalized_matched = matched_course.lower().replace(".", "")
            
            for course in self.database:
                db_name = course["nazwa"].strip().lower().replace(".", "")
                
                if normalized_matched and (normalized_matched in db_name or db_name in normalized_matched):
                    context = course
                    break
            
            if not context:
                context_str = "Brak szczegółowych danych w bazie wiedzy dla tego zapytania."
            else:
                context_str = json.dumps(context, indent=2, ensure_ascii=False)

        system_chat_prompt = (
            "Jesteś asystentem Dziekanatu UG. Udzielasz informacji na podstawie danych w formacie JSON.\n\n"
            "ZASADY KRYTYCZNE:\n"
            "1. TARCZA (ZŁAGODZONA): Odmawiaj TYLKO jeśli student prosi o napisanie kodu, algorytmu lub rozwiązanie zadania. "
            "Pytania o przedmioty mające w nazwie słowo 'programowanie' to pytania organizacyjne i MUSISZ na nie odpowiadać na podstawie danych.\n"
            "2. SYNONIMY: Jeśli student pyta o 'zaliczenie', 'sprawdzanie wiedzy', 'wymogi' lub 'kolokwia', szukaj informacji w sekcji 'ocenianie'.\n"
            "3. PRAWDA DANYCH: Jeśli w JSON-ie faktycznie nie ma jakiejś sekcji, powiedz wprost: 'Syllabus nie przewiduje...'. "
            "Jeśli przekazano Ci 'Listę wszystkich dostępnych przedmiotów' (GLOBALNE), po prostu ją sformatuj i wypisz.\n"
            "4. LEKTURY: Jeśli padnie pytanie o książki, literaturę lub e-zasoby, zawsze wyświetlaj obie te sekcje z ikonami 📚 i 🌐.\n"
            "5. Bądź kulturalny przy powitaniach i pożegnaniach.\n\n"
            "Oto dane do wykorzystania:\n"
            "{context}"
        )

        chat_prompt = ChatPromptTemplate.from_messages([
            ("system", system_chat_prompt),
            ("user", "{query}")
        ])

        conversation_chain = chat_prompt | self.llm
        answer = conversation_chain.invoke({"context": context_str, "query": user_query})
        output_text = answer.content

        self._update_memory(user_query, output_text)
        return output_text

    def _update_memory(self, user_query: str, output_text: str):
        self.chat_history.append({"role": "Student", "content": user_query})
        self.chat_history.append({"role": "AI", "content": output_text})
        if len(self.chat_history) > 6:
            self.chat_history = self.chat_history[-6:]

if __name__ == "__main__":
    print("Inicjalizacja Inteligentnego Asystenta Sylabusów...")
    try: # try na wypadek błędu połączenia z OpenAI API
        bot = SyllabusChatbot("knowledge_base.json")
        print("Bot gotowy do rozmowy! Wpisz 'exit' aby wyjść.\n")
        
        while True:
            pytanie = input("Student: ")
            if pytanie.lower() == 'exit':
                print("Do widzenia!")
                break
                
            if not pytanie.strip():
                continue
            
            try: # gdy będzie problem z połącznieme w trakcie rozmowy    
                odpowiedz = bot.ask(pytanie)
                print(f"\nAI:\n{odpowiedz}\n")
            except Exception as api_err:
                print(f"\n[SYSTEM] Problem z serwerem API (Sprawdź internet): {api_err}\n")
                
            print("-" * 40)
            
    except Exception as e:
        print(f"\n[BŁĄD KRYTYCZNY STARTU] Nie udało się zainicjalizować bota. Powód: {e}")