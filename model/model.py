from database.parco_DAO import ParcoDAO
from database.escursione_DAO import EscursioneDAO
from database.punto_interesse_DAO import PuntoInteresseDAO

class Model:
    def __init__(self):
        self.escursioni_map = {} # Mappa ID escursione -> oggetti Escursione
        self.punti_interesse_map = {} # Mappa ID punto di interesse -> oggetti PuntoInteresse

        self._pacchetto_ottimo = []
        self._valore_ottimo: int = -1
        self._costo = 0


        # Caricamento
        self.load_escursioni()
        self.load_punti_interesse()
        self.load_relazioni()

    @staticmethod
    def load_parchi():
        """ Restituisce tutti i parchi disponibili """
        return ParcoDAO.get_parchi()

    def load_escursioni(self):
        """ Carica tutte le escursioni in un dizionario [id, Escursione]"""
        self.escursioni_map = EscursioneDAO.get_escursioni()

    def load_punti_interesse(self):
        """ Carica tutti i punti di interesse in un dizionario [id, PuntoInteresse]"""
        self.punti_interesse_map = PuntoInteresseDAO.get_punti_interesse()



   # Funzione per interrogare il database e salvare le relazioni, carica per ogni escursione e puntointeresse il
    #     proprio insieme
    def load_relazioni(self):
        """
            Interroga il database per ottenere tutte le relazioni fra escursioni e punti di interesse e salvarle nelle strutture dati
            Collega escursione <-> punti di interesse.
            --> Ogni Escursione ha un set di PuntoInteresse.
            --> Ogni PuntoInteresse ha un set di Escursioni.
        """
        relazioni = EscursioneDAO.get_escursioni_punti_interesse()      # prendo relazioni fornite dal dao
        if relazioni is not None:                 # se ne ho, le scorro tutte
            for r in relazioni:
                id_escursione = r["id_escursione"]
                id_punto = r["id_punto_interesse"]

                if id_escursione in self.escursioni_map and id_punto in self.punti_interesse_map:  # se ci sono nelle mappe
                    escursione = self.escursioni_map[id_escursione]     # recupero l'oggetto escursione dalla struttura dati
                    punto = self.punti_interesse_map[id_punto]      # recupero l'oggetto punto di interesse dalla struttura dati

                    escursione.punti_interesse.add(punto)     # aggiungo il punto all'inisieme di quell'escursione
                    punto.escursioni.add(escursione)        # aggiungo l'escursione all'insieme di quel punto
            # ogni oggetto ha come attributo insieme di punti_interesse/escursioni associati a cui aggiungere i valori



   # Funzione per creare il pacchetto ottimale, rispettando i vincoli dati
    def genera_pacchetto(self, id_parco: str, max_giorni: int = None, max_budget: float = None):
        """
        Calcola il pacchetto di escursioni ottimale per un parco rispettando i vincoli di durata, budget e punti di interesse unici.
        :param id_parco: id del parco
        :param max_giorni: numero massimo di giorni (può essere None --> nessun limite)
        :param max_budget: costo massimo del pacchetto (può essere None --> nessun limite)

        :return: self._pacchetto_ottimo (una lista di oggetti Escursione)
        :return: self._costo (il costo del pacchetto)
        :return: self._valore_ottimo (il voto complessivo dei visitatori per il pacchetto)
        """
        # Riceve i dati inseriti dall'utente dall'interfaccia grafica (parco scelto, i giorni e budget massimo) e prepara
        #      il necessario prima di dare il via alla ricorsione (calcolo)
        self._pacchetto_ottimo = []       # resetto le variabili, altrimenti restrerebbe il calcolo del pacchetto precedente
        self._costo = 0
        self._valore_ottimo = -1
        self._escursioni_parco = []

        # Filtro le escursioni per considerare solamente quelle appartenenti al parco selezionato
        for escursione in self.escursioni_map.values():
            if escursione.id_parco == id_parco:
                self._escursioni_parco.append(escursione)    # aggiungo escursioni con quel parco alla struttura dati

        # Salvo qui i valori limite, cosi la fz ricorsiva puo leggerli direttamente, senza doverli passare ogni volta
        self._max_giorni = max_giorni
        self._max_budget = max_budget

        # Avvio la ricorsione, che aggiorna ad ogni esplorazione i valori inizializzati "self" in questa funzione
        self._ricorsione(0, [], 0, 0, 0, set())
        return self._pacchetto_ottimo, self._costo, self._valore_ottimo



   # Funzione per la ricorsione
    def _ricorsione(self, start_index: int, pacchetto_parziale: list, durata_corrente: int, costo_corrente: float, valore_corrente: int, punti_usati: set):
        """ Algoritmo di ricorsione che deve trovare il pacchetto che massimizza il voto complessivo dei visitatori"""
        # Controllo se il pacchetto parziale è il migliore fino ad ora
        if valore_corrente > self._valore_ottimo:
            self._valore_ottimo = valore_corrente
            self._pacchetto_ottimo = pacchetto_parziale.copy()   # faccio una copia del parziale fino a questo momento, per non sovrascrivere
            self._costo = costo_corrente
        # Salvo direttamente i valori migliori nelle variabili della classe

        # Scorro le escursioni del parco da start_index (parametro) per non ripetere quelle già considerate
        for i in range(start_index, len(self._escursioni_parco)):
            escursione = self._escursioni_parco[i]

            # Calcoli parziali
            nuova_durata = durata_corrente + escursione.durata_giorni
            nuovo_costo = costo_corrente + escursione.costo
            punti_escursione = escursione.punti_interesse

            # Se tutti i vincoli sono verificati con una funzione, aggiorno la soluzione parziale, il valore e i punti usati
            if self._vincoli_rispettati(nuova_durata, nuovo_costo, punti_escursione, punti_usati):
                pacchetto_parziale.append(escursione)       # aggiungo al pacchetto che sto costruendo
                for punto in punti_escursione:
                    punti_usati.add(punto)                       # aggiungo i punti utilizzati

                valore_aggiunto = 0
                for pi in punti_escursione:
                    valore_aggiunto += pi.voto_visitatori          # sommo i voti assegnati in ogni punto
                nuovo_valore = valore_corrente + valore_aggiunto  # aggiorno il nuovo valore da passare alla prossima ricorsione

                # Ricorro di nuovo con l'indice successivo
                self._ricorsione(i + 1, pacchetto_parziale, nuova_durata, nuovo_costo, nuovo_valore, punti_usati)

                pacchetto_parziale.pop()            # faccio backtracking
                # devo rimuovere i punti aggiunti prima, così da riportare l'insieme allo stato iniziale.
                for punto in punti_escursione:
                    punti_usati.discard(punto)


    # Funzione per verificare se l'aggiunta di una escursione rispetta i vincoli dati
    def _vincoli_rispettati(self, nuova_durata, nuovo_costo, punti_esc, punti_usati):
        vincoli_sono_ok = True
        if self._max_giorni is not None:         # controllo sulla durata massima
            if nuova_durata > self._max_giorni:
                vincoli_sono_ok = False

        if self._max_budget is not None:     # controllo sul budget massimo
            if nuovo_costo > self._max_budget:
                vincoli_sono_ok = False

        for punto in punti_esc:          # controllo che nessun punto sia gia usato
            if punto in punti_usati:
                vincoli_sono_ok = False
        return vincoli_sono_ok
