import signal
from socket import AF_INET, socket, SOCK_STREAM
from threading import Thread
import sys

users = {}          # Dizionario che associa ad ogni client (socket) il suo username.
addresses = {}      # Dizionario che associa ad ogni client (socket) il suo indirizzo.

ADDRESS = 'localhost'
PORT = 53000
BUFSIZ = 1024
SERVER = socket(AF_INET, SOCK_STREAM)
MAX_CONN_QUEUE = 5


def handle_connections():
    """ Accetta le connessioni in entrata """
    while True:
        try:
            # Accetta la connessione in entrata.
            client, client_address = SERVER.accept()
            print("%s:%s si è connesso." % client_address)

            # Invia le istruzioni per iniziare la chat al client.
            client.send(bytes("Ciao! Scrivi il tuo nome e premi invio per confermarlo!", "utf8"))

            # Registra l'indirizzo del client.
            addresses[client] = client_address

            # Crea un nuovo thread che da ora in poi si occuperà di gestire quel client.
            Thread(target=handle_client, args=(client,)).start()
        
        except Exception as e:
            print(f"Errore durante l'accept della connessione in entrata: {e}")
        

def handle_client(client):
    """ Gestisce la connessione con il client passato per parametro. """

    try:
        # Il primo messaggio inviato dal client dovrebbe essere l'username.
        username = client.recv(BUFSIZ).decode("utf8")

        # Se così non fosse e il client provasse a chiudere la connessione prima di inviare l'username alza una eccezione che termina la connessione.
        if not username or username == bytes("/quit", "utf8"):
            raise Exception

        # Invia un messaggio di benvenuto al client e fornisce istruzioni su come chiudere la connessione.
        welcome_message = f'Benvenuto {username}! Per uscire dalla chat scrivi "/quit".'
        client.send(bytes(welcome_message, "utf8"))

        # Notifica tutti i client connessi della nuova connessione.
        msg = f"{username} si è connesso alla chat."
        broadcast(bytes(msg, "utf8"))

        # Memorizza l'username del client.
        users[client] = username
    except Exception as e:
        print(f"Errore durante la ricezione dell'username dal client {addresses[client]}")
        del addresses[client]
        client.close()
        return
    
    connected = True

    # Gestisce tutti i messaggi successivi con il client.
    while connected:
        try:
            # Riceve il messaggio e se è diverso da /quit lo inoltra a tutti.
            msg = client.recv(BUFSIZ)
            if msg and msg != bytes("/quit", "utf8"):
                broadcast(msg, username + ": ")
            else:
                # Se era /quit cancella i suoi dati e notifica tutti della sua dipartita.
                connected = False
        except Exception as e:
            connected = False
    print(f"{addresses[client]} si è disconnesso.")
    del users[client]
    del addresses[client]
    broadcast(bytes("%s ha abbandonato la chat." % username, "utf8"))
    client.close()

def broadcast(msg, prefix=""):  # il prefisso viene scritto prima del messaggio, usato per segnalare il nome utente.
    """ Invia un messaggio in broadcast a tutti i client registrati. """
    for user in users:
        try:
            user.send(bytes(prefix, "utf8") + msg)
        except Exception as e:
            print(f"Errore durante l'invio del messaggio a {addresses[user]}; {e}")


# Se viene eseguito come main e non importato come modulo
if __name__ == "__main__":
    try:
        if len(sys.argv) == 3:
            ADDRESS = sys.argv[1]
            PORT = int(sys.argv[2])
        # Binding all'indirizzo specificato e messa in ascolto.
        SERVER.bind( (ADDRESS, PORT) )
        SERVER.listen(MAX_CONN_QUEUE)
        print("Server pronto e in ascolto sulla porta: ", PORT)

        # Avvia il thread che gestisce le connessioni in entrata.
        ACCEPT_THREAD = Thread(target = handle_connections)
        ACCEPT_THREAD.start()
        ACCEPT_THREAD.join()    # Non termina ma aspetta la fine di ACCEPT_THREAD.
    except Exception as e:
        print(f"Il server non è riuscito a mettersi in ascolto sulla porta {PORT}.")
        print(f"Assicurati che la porta {PORT} non sia utilizzata da un altro processo.")
        print("Eccezione: " + str(e))
    finally:
        print("Sto chiudendo il server...")
        SERVER.close()  # Chiude il server