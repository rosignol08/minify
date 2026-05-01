import paho.mqtt.client as mqtt

IP_BROKER = "10.225.220.148"
def on_connect(client, userdata, flags, rc): # Callback connexion broker
    print("Connecté " + str(rc))
    client.subscribe("musique")
    #client.publish("resultats", "ils ont vote") # Publication d'un message



def on_message(client, userdata, msg): # Callback subscriber
    #global resulta0, resulta1
    print(f"Message reçu : {msg.topic} {msg.payload.decode()}") #decode pour enlever le b'' truc là
    truc_a_stoquer = msg.payload.decode()


client = mqtt.Client() # Création d'une instance client

client.on_connect = on_connect # Assignation des callbacks

client.on_message = on_message

client.connect(IP_BROKER, 1883, 60)  # Remplacez par l'IP du broker



client.loop_forever() # pour attendre les messages
