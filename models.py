from pydantic import BaseModel, Field
from typing import List, Dict

class Literatura(BaseModel):
    podstawowa: List[str] = Field(
        default_factory=list, # default_factory=list zwraca nam nową pustą listę specjalnie dla tego obiektu
        description="Lista obowiązkowych lektur wymaganych do zaliczenia przedmiotu"
    )
    uzupelniajaca: List[str] = Field(
        default_factory=list,
        description="Dodatkowa literatura dla zainteresowanych studentów, nieobowiązkowa"
    )

class EfektUczenia(BaseModel):
    efekt_kierunkowy: str = Field(description="Kod efektu uczenia się dla kierunku, np. [INFL3_K02]")
    efekt_z_przedmiotu: str = Field(description="Opis konkretnej umiejętności nabywanej na zajęciach")
    sposob_weryfikacji: str = Field(description="Metoda sprawdzenia efektu, np. kolokwium, projekt, odpowiedź ustna")

class Ocenianie(BaseModel):
    typ: str = Field(description="Rodzaj składowej oceny, np. 'projekt', 'wejściówki', 'kolokwium'")
    prog: str = Field(description="Minimalny wynik wymagany do zaliczenia składowej, np. '50.0%'")
    waga: str = Field(description="Udział składowej w ocenie końcowej, np. '50.0%'")

class SyllabusModel(BaseModel):
    nazwa: str = Field(default="", description="Pełna nazwa przedmiotu akademickiego")
    kod: str = Field(default="", description="Unikalny kod przedmiotu, zazwyczaj zaczynający się od PG_")
    kierunek: str = Field(default="", description="Kierunek studiów, np. 'Informatyka'")
    ects: str = Field(default="", description="Liczba punktów ECTS przypisana do przedmiotu")
    forma_zaliczenia: str = Field(default="", description="Sposób końcowego zaliczenia przedmiotu, np. 'egzamin' lub 'zaliczenie'")

    odpowiedzialny: str = Field(
        default="",
        description="Imię i nazwisko osoby odpowiedzialnej za przedmiot, jest to też osoba prowadząca wykłady"
    )
    prowadzacy: List[str] = Field(
        default_factory=list,
        description="Lista pozostałych osób prowadzących zajęcia (ćwiczenia, laboratoria) wymienionych w sylabusie"
    )
    
    godziny: Dict[str, str] = Field(
        default_factory=dict,
        description="Zestawienie godzinowe dla form zajęć: wykład, ćwiczenia, laboratorium, projekt, seminarium"
    )
    aktywnosc_studenta: Dict[str, str] = Field(
        default_factory=dict,
        description="Podział godzinowy pracy studenta: zajęcia dydaktyczne, konsultacje, praca własna"
    )
    
    literatura: Literatura = Field(
        default_factory=Literatura,
        description="Podział lektur na podstawowe i uzupełniające"
    )
    
    ezasoby: List[str] = Field(
        default_factory=list,
        description="Lista adresów URL do zasobów online lub platform e-learningowych"
    )

    efekty_uczenia: List[EfektUczenia] = Field(
        default_factory=list,
        description="Szczegółowa lista efektów uczenia się wraz ze sposobem ich weryfikacji"
    )
    
    ocenianie: List[Ocenianie] = Field(
        default_factory=list,
        description="Składowe oceny końcowej, ich progi zaliczeniowe oraz wagi"
    )
    
    program: List[str] = Field(
        default_factory=list,
        description="Treści programowe przedmiotu rozbite na punkty"
    )
    
    cel: str = Field(default="", description="Główny cel dydaktyczny przedmiotu")
    
    praktyki: str = Field(
        default="Nie dotyczy",
        description="Informacja o praktykach zawodowych; jeśli brak informacji, wpisz 'Nie dotyczy'"
    )