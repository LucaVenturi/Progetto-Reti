from socket import AF_INET, socket, SOCK_STREAM, error as SocketError
from threading import Thread
import tkinter as tkt
from tkinter import simpledialog, messagebox

def create_window():
    global window, my_msg, msg_text
    window = tkt.Tk()
    window.title("Chat di gruppo")

    window.grid_columnconfigure(0, weight=1)
    window.grid_rowconfigure(0, weight=1)
    
    # Crea il Frame che contiene i messaggi
    messages_frame = tkt.Frame(window)
    messages_frame.grid(row=0, column=0, sticky="nsew")
    messages_frame.grid_rowconfigure(0, weight=1)
    messages_frame.grid_columnconfigure(0, weight=1)
    
    # Crea una variabile di tipo StringVar per i messaggi da inviare.
    my_msg = tkt.StringVar()
    my_msg.set("Scrivi qui...")

    # Crea una scrollbar per navigare tra i messaggi precedenti.
    scrollbar = tkt.Scrollbar(messages_frame)
    scrollbar.grid(row=0, column=1, sticky="ns")

    # Crea un Text widget che contiene tutti i messaggi e le comunicazioni dal server. La listbox non andava a capo.
    msg_text = tkt.Text(messages_frame, height=15, wrap="word", yscrollcommand=scrollbar.set)
    msg_text.grid(row=0, column=0, sticky="nsew")
    msg_text.config(state=tkt.DISABLED)

    scrollbar.config(command=msg_text.yview)

    # Crea il campo di input e lo associa a my_msg.
    entry_field = tkt.Entry(window, textvariable=my_msg)
    entry_field.bind("<Return>", send)
    entry_field.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

    # Crea il tasto invio e binda anch'esso a "send".
    send_button = tkt.Button(window, text="Invio", command=send)
    send_button.grid(row=2, column=0, pady=5)

    # Specifica le azioni da eseguire alla chiusura della finestra.
    window.protocol("WM_DELETE_WINDOW", on_closing)

def printerror(err_msg):
    """ Funzione che avverte l'utente di un errore. """
    print(err_msg)
    messagebox.showerror("Errore", err_msg)

def receive():
    global app_closing
    while True:
        try:
            #quando viene chiamata la funzione receive, si mette in ascolto dei messaggi che
            #arrivano sul socket
            msg = client_socket.recv(BUFSIZ).decode("utf8")

            # Attiva la textbox per inserire il messaggio e poi la ridisattiva.
            msg_text.config(state=tkt.NORMAL)
            msg_text.insert(tkt.END, msg + "\n")
            msg_text.config(state=tkt.DISABLED)
            msg_text.yview(tkt.END)

        except Exception as e:
            # Se l'app è in fase di chiusura, ovvero l'utente ha cliccato la X o inviato /quit, il thread finisce.
            if app_closing:
                break

            # Altrimenti c'è stato un errore con la connessione e si chiede all'utente se vuole provare a riconnettersi.
            printerror(f"Errore: {e}")
            response = messagebox.askyesno("Connessione persa", "La connessione con il server è stata persa. Vuoi riconnetterti?")

            # In ogni caso chiudo il socket.
            if client_socket:
                    client_socket.close()

            # Se vuole riconnettersi riprova la connessione
            if response:
                connect_to_server()
            else:
                # Altrimenti esce
                window.quit()
                exit()

def send(event=None):
    """La funzione che gestisce l'invio dei messaggi. è bindata al bottone invio e al tasto ENTER"""
    
    global app_closing

    # my_msg è bindata alla entry. Quindi ne prendo il contenuto e poi la libero.
    msg = my_msg.get()
    my_msg.set("")

    # Controllo che non superi il buffer, in realtà non causerebbe particolari errori, verrenne semplicemente inviato come due o più messaggi.
    if len(msg) > BUFSIZ:
        printerror(f"Puoi inviare al massimo {BUFSIZ} caratteri.")
        return

    # Invia il messaggio sul socket.
    try:
        client_socket.send(bytes(msg, "utf8"))
    except SocketError as e:
        printerror(f"Errore durante l'invio del messaggio: {e}")
    except Exception as e:
        printerror(f"Errore: {e}")
    
    # Se il messaggio è /quit chiude la connessione. Notare che lo invia comunque al server prima di chiudere per comunicargli di chiudere la connessione.
    if msg == "/quit":
        app_closing = True
        if client_socket:
            client_socket.close()
        window.quit()


def on_closing(event=None):
    """ La funzione che viene invocata quando viene chiusa la finestra della chat. In pratica imposta il messaggio a /quit e usa send() per inviarlo al server chiudendo la connessione. """
    global app_closing
    
    app_closing = True  # Setto app_closing a True per comunicare al thread receive che la perdita di connessione imminente è voluta e di non provare a riconnettersi.

    # Per chiudere il client setta il messaggio a /quit e lo invia al server.
    my_msg.set("/quit")
    send()


def ask_server_info():
    """ Crea una Dialog che chiede all'utente l'host e la porta del server a cui connettersi. """

    result = ServerInfoDialog(window).result

    # Se l'utente non clicca su ok ma chiude la dialog.
    if result == None:
        exit()

    HOST, PORT = result

    # Se manca un dato uso quelli di default.
    if not HOST:
        HOST = 'localhost'
    if not PORT or not isinstance(PORT, int):
        PORT = 53000

    return HOST, PORT

def connect_to_server():
    """ Si connette al server specificato tramite TCP. """

    global client_socket, receive_thread
    flag = True
    while flag:
        try:
            client_socket = socket(AF_INET, SOCK_STREAM)
            client_socket.connect(ADDRESS)

            receive_thread = Thread(target=receive)
            receive_thread.start()

            return client_socket, receive_thread    # se non ci sono state eccezioni esce.
        except Exception as e:
            # Se ci sono eccezioni chiede se si vuole riprovare. Il flag è la risposta dell'utente.
            err_msg = f"Errore durante la connessione al server: {e} \n \n Vuoi riprovare?"
            flag = messagebox.askretrycancel("Errore", err_msg)
            if client_socket:
                client_socket.close
    # Se dopo l'eccezione l'utente ha risposto no esco da tutto.
    window.quit()
    exit()

class ServerInfoDialog(tkt.simpledialog.Dialog):
    """ Una classe che implementa la mia versione della simpledialog per chiedere HOST e PORT. """
    def body(self, master):
        tkt.Label(master, text="Server Host:").grid(row=0, column=0, padx=5, pady=5)
        tkt.Label(master, text="Server Port:").grid(row=1, column=0, padx=5, pady=5)

        self.host_entry = tkt.Entry(master)
        self.port_entry = tkt.Entry(master)

        self.host_entry.grid(row=0, column=1, padx=5, pady=5)
        self.port_entry.grid(row=1, column=1, padx=5, pady=5)

        self.host_entry.insert(0, "localhost")
        self.port_entry.insert(0, "53000")

        return self.host_entry  # Il focus iniziale è sulla entry per l'host.

    # Funzione chiamata dalla simpledialog al click su OK.
    def apply(self):
        self.result = (self.host_entry.get(), int(self.port_entry.get()))

if __name__ == "__main__":
    global BUFSIZ, ADDRESS, app_closing

    app_closing = False
    BUFSIZ = 1024

    create_window()                 # Crea finestra di chat.
    ADDRESS = ask_server_info()     # Crea una dialog che chiede all'utente HOST e PORT.
    connect_to_server()             # Avvia una connessione TCP verso il server dall'indirizzo specificato in ADDRESS.

    tkt.mainloop()                  # Avvia l'esecuzione della Finestra Chat.