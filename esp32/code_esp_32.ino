// --------------------------------------------------------------------------------------------------------------------
// Multi-tâches cooperatives : solution basique mais efficace :-)
// --------------------------------------------------------------------------------------------------------------------

// --------------------------------------------------------------------------------------------------------------------
// unsigned int waitFor(timer, period)
// Timer pour taches périodiques
// configuration :
//  - MAX_WAIT_FOR_TIMER : nombre maximum de timers utilisés
// arguments :
//  - timer  : numéro de timer entre 0 et MAX_WAIT_FOR_TIMER-1
//  - period : période souhaitée
// retour :
//  - nombre de périodes écoulées depuis le dernier appel
// --------------------------------------------------------------------------------------------------------------------
#include <vector>
#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define MAX_WAIT_FOR_TIMER 3

unsigned long waitFor(int timer, unsigned long period)
{
    static unsigned long last_period[MAX_WAIT_FOR_TIMER]; // il y a autant de timers que de tâches
    unsigned long current = micros() / period;            // numéro de période
    unsigned long delta = current - last_period[timer];   // gère le wrap-around
    if (delta)
        last_period[timer] = current; // mise à jour si déclenchement
    return delta;                     // nombre de periode depuis le dernier appel
}

#define SCREEN_WIDTH 128 // OLED display width, in pixels
#define SCREEN_HEIGHT 64 // OLED display height, in pixels

// Declaration for an SSD1306 display connected to I2C (SDA, SCL pins)
#define OLED_RESET 16 // Reset pin # (or -1 if sharing Arduino reset pin)
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

#define NUMFLAKES 10 // Number of snowflakes in the animation example

#define LOGO_HEIGHT 16
#define LOGO_WIDTH 16

#define BUTTON_PIN 23

#define REST 0
#define NOTE_G4 392
#define NOTE_A4 440
#define NOTE_B4 494
#define NOTE_C5 523
#define NOTE_D5 587
#define NOTE_E5 659
#define NOTE_F5 698
#define NOTE_G5 784
#define NOTE_GS4 415 // Sol Dièse
#define NOTE_AS5 932 // La Dièse
#define NOTE_FS5 740 // Fa Dièse
#define NOTE_G5 784
#define NOTE_A5 880
#define NOTE_C6 1047 // Do Octave 6

static const unsigned char PROGMEM logo_bmp[] =
    {B00000000, B11000000,
     B00000001, B11000000,
     B00000001, B11000000,
     B00000011, B11100000,
     B11110011, B11100000,
     B11111110, B11111000,
     B01111110, B11111111,
     B00110011, B10011111,
     B00011111, B11111100,
     B00001101, B01110000,
     B00011011, B10100000,
     B00111111, B11100000,
     B00111111, B11110000,
     B01111100, B11110000,
     B01110000, B01110000,
     B00000000, B00110000};

enum
{
    EMPTY,
    FULL
};

struct mailbox_t
{
    int state;
    int val;
};

typedef struct mailbox_t mailbox_t;

mailbox_t mb_photo = {EMPTY, 0};
mailbox_t mb_led = {EMPTY, 0};
mailbox_t mb_interupt = {EMPTY, 0}; // 0 = clignote, 1 = stop
mailbox_t mb_son = {EMPTY, 0};

bool led_coupe = false;
bool jouer_son = false;
struct ctx_timer_t
{
    int timer;            // num du timer pour cette tâche utilisé par WaitFor
    unsigned long period; // periode de clignotement
};

typedef struct
{
    int timer;            // num du timer pour cette tâche utilisé par WaitFor
    unsigned long period; // periode de clignotement
    int pin;              // num de la broche sur laquelle est la LED
    int etat;             // etat interne de la led
} ctx_led_t;

typedef struct
{
    int timer;            // num de timer utilisé par WaitFor
    unsigned long period; // periode d'affichage
    char mess[20];
} ctx_mess_t;

// les partitions :
std::vector<int> partition = {};

// Calculé sur la base 1000 / durations[]
std::vector<int> temps = {};

void init_led(ctx_led_t *ctx, int timer, unsigned long period, byte pin);
void step_led(ctx_led_t *ctx, mailbox_t *mb_led, mailbox_t *mb_interupt);
// tâche qui arrête le clignotement de la LED si on recoit un s depuis le clavier
void step_tache_interruption();
void step_tache_isr();
void coupe_led(mailbox_t *mb_interupt);
void init_mess(ctx_mess_t *ctx, int timer, unsigned long period, const char *mess);
void step_mess(ctx_mess_t *ctx);
int init_lum(struct ctx_timer_t *chrono, int timer_numero, unsigned long period);
int lum(ctx_timer_t *chrono, struct mailbox_t *mb_photo, mailbox_t *mb_led);
int oled(mailbox_t *mb);
void setupoled();
void joue_son(std::vector<int> partition, std::vector<int> temps, struct mailbox_t *mb_son);

// mqtt

#include <WiFi.h>
#include <PubSubClient.h>

const char *ssid = "5G";
const char *password = "12345678";
const char *mqttServer = "192.168.1.69"; // IP of the Raspberry Pi
const int mqttPort = 1883;
const char *mqttTopic = "flux";
const char *mqttTopic_envoie = "control";

WiFiClient espClient;
PubSubClient client(espClient);

const int ledPin = 2;
int index_note = 0;
String musiqueNom = "";
unsigned long musiqueDureeAnnonceeMs = 0;
bool musiqueChargee = false;

void parseFluxPacket(const String &rawPayload)
{
    String payload = rawPayload;
    payload.trim();
    if (payload.length() == 0)
        return;

    bool isLastPacket = payload.endsWith(".");
    if (isLastPacket)
    {
        payload.remove(payload.length() - 1);
    }

    // Premier paquet: "nom;duree"
    if (payload.indexOf(',') < 0 && payload.indexOf(';') >= 0)
    {
        int sep = payload.indexOf(';');
        musiqueNom = payload.substring(0, sep);
        musiqueDureeAnnonceeMs = payload.substring(sep + 1).toInt();
        partition.clear();
        temps.clear();
        musiqueChargee = false;
        index_note = 0;
        Serial.print("Nouvelle musique: ");
        Serial.print(musiqueNom);
        Serial.print(" (ms annonces: ");
        Serial.print(musiqueDureeAnnonceeMs);
        Serial.println(")");
        return;
    }

    int start = 0;
    while (start < payload.length())
    {
        int end = payload.indexOf(';', start);
        if (end < 0)
            break;

        String item = payload.substring(start, end);
        item.trim();
        if (item.length() > 0)
        {
            int comma = item.indexOf(',');
            if (comma > 0)
            {
                String noteStr = item.substring(0, comma);
                String dureeStr = item.substring(comma + 1);
                int freq = noteStr.toInt();
                int dureeMs = dureeStr.toInt();

                if (freq >= 0 && dureeMs > 0)
                {
                    partition.push_back(freq);
                    // joue_son attend des microsecondes dans waitFor(... *1000)
                    temps.push_back(dureeMs);
                }
            }
        }

        start = end + 1;
    }

    if (isLastPacket)
    {
        musiqueChargee = !partition.empty() && partition.size() == temps.size();
        Serial.print("Fin reception musique. Notes recues: ");
        Serial.println((int)partition.size());
    }
}

// Callback function is called when a message is received
void callback(char *topic, byte *payload, unsigned int length)
{
    String topicStr = String(topic);
    String msg;
    msg.reserve(length + 1);
    for (unsigned int i = 0; i < length; i++)
    {
        msg += (char)payload[i];
    }

    if (topicStr == mqttTopic)
    {
        parseFluxPacket(msg);
        return;
    }

    if (msg == "ON")
    {
        digitalWrite(ledPin, HIGH);
    }
    else if (msg == "OFF")
    {
        digitalWrite(ledPin, LOW);
    }

    Serial.print("Message recu [");
    Serial.print(topicStr);
    Serial.print("]: ");
    Serial.println(msg);
}
//

int init_lum(struct ctx_timer_t *chrono, int timer_numero, unsigned long period)
{
    chrono->timer = timer_numero;
    chrono->period = period;
    return -1;
}

int lum(ctx_timer_t *chrono, struct mailbox_t *mb_photo, mailbox_t *mb_led)
{
    if (mb_photo->state != EMPTY || mb_led->state != EMPTY)
    {
        return -1;
    } // attend que la mailbox soit vide
    if (!waitFor(chrono->timer, chrono->period))
    {
        return -1;
    }
    int valeur_lumiere = analogRead(36); // 36 c'est le pin
    int pourcentage = map(valeur_lumiere, 0, 4095, 0, 100);
    mb_photo->val = pourcentage;
    mb_photo->state = FULL;
    mb_led->val = 10000 / pourcentage * 1000;
    mb_led->state = FULL;
}

int oled(mailbox_t *mb)
{
    if (mb->state != FULL)
        return -1; // attend que la mailbox soit pleine
    display.clearDisplay();
    display.setTextSize(2); // Draw 2X-scale text
    display.setTextColor(WHITE);
    display.setCursor(10, 0);
    display.println(mb->val);
    display.display(); // Show initial text
    delay(10);
    mb->state = EMPTY;
}

void setupoled()
{
    Serial.begin(9600);
    Wire.begin(4, 15); // pins SDA , SCL
    // SSD1306_SWITCHCAPVCC = generate display voltage from 3.3V internally
    if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C))
    { // Address 0x3D for 128x64
        Serial.println(F("SSD1306 allocation failed"));
        for (;;)
            ; // Don't proceed, loop forever
    }
    display.display();
    delay(2000); // Pause for 2 seconds
    // Clear the buffer
    display.clearDisplay();
    display.drawPixel(10, 10, WHITE);
    display.display();
}

//--------- définition de la tache Led

void init_led(ctx_led_t *ctx, int timer, unsigned long period, byte pin)
{
    ctx->timer = timer;
    ctx->period = period;
    ctx->pin = pin;
    ctx->etat = 0;
    pinMode(pin, OUTPUT);
    digitalWrite(pin, ctx->etat);
}

void step_led(ctx_led_t *ctx, mailbox_t *mb_led, mailbox_t *mb_interupt)
{
    if (mb_interupt->state == FULL)
    {
        return;
    }
    if (mb_led->state == FULL)
    {
        // si la mailbox est pleine
        ctx->period = mb_led->val;
        mb_led->state = EMPTY;
    }
    if (!waitFor(ctx->timer, mb_led->val))
        return;                        // sort s'il y a moins d'une période écoulée
    digitalWrite(ctx->pin, ctx->etat); // ecriture
    ctx->etat = 1 - ctx->etat;         // changement d'état
}

void coupe_led(mailbox_t *mb_interupt)
{
    if (Serial.available() > 0)
    {
        String recu = Serial.readString();
        recu.trim();
        if (recu == "s")
        { // si on a recu un s on arrete de cliginoter
            led_coupe = !led_coupe;
            Serial.print("j'ai capté mec"); //,DEC
            Serial.println(led_coupe);
            mb_interupt->state = FULL;
            mb_interupt->val = led_coupe;
        }
        else
        {

            mb_interupt->state = EMPTY;
            mb_interupt->val = led_coupe;
        }
    }
}

// Pour jouer une note (Remplace tone)
// void ma_fonction_tone(int frequence, int duree, struct mailbox_t * mb_son) {
// partition et temps font la meme taille normalement
// for(int i = 0; i < partition.size(); i++){
//  ma_fonction_tone( partition[i],temps[i],mb_son);
//  //delay(temps[i] * 0.70);
//}
void joue_son(std::vector<int> partition, std::vector<int> temps, struct mailbox_t *mb_son)
{
    if (mb_son->state == EMPTY)
    {
        ledcWriteTone(0, 0);
        index_note = 0;
        return;
    }
    if (waitFor(3, temps[index_note] * 1000))
    {
        ledcWriteTone(0, partition[index_note]);
        index_note++;
        if (index_note >= partition.size())
        {
            index_note = 0;
            // mb_son->state = EMPTY; si on veut que ça se coupe à la fin on decommente ça
        }
    }
}

void step_bouton_musique(struct mailbox_t *mb_son)
{
    // check l'etat du btn
    if (digitalRead(BUTTON_PIN) == LOW)
    {
        // anti-rebond simple
        delay(50);
        if (digitalRead(BUTTON_PIN) == LOW)
        {
            jouer_son = !jouer_son;
            Serial.println("la valeur est maintenant : ");
            Serial.println(jouer_son);
            if (!jouer_son)
            {
                Serial.println("Bouton pressé : stop Musique !");
                mb_son->state = EMPTY;
                client.publish(mqttTopic_envoie, "stop");
                // att que le bouton soit release pour pas boucler
            }
            else
            {
                Serial.println("Bouton pressé : joue Musique !");
                mb_son->state = FULL;
                client.publish(mqttTopic_envoie, "joue");

                // att que le bouton soit release pour pas boucler
            }
            while (digitalRead(BUTTON_PIN) == LOW)
                ;
        }
    }
}

// bouton interuption
// void step_serial(){
//  led_coupe = !led_coupe;
//}

// void step_tache_interruption(){
//   attachInterrupt(0, step_serial, FALLING); //mettre 1 si 0 marche pas
// }

//--------- definition de la tache Mess

void init_mess(ctx_mess_t *ctx, int timer, unsigned long period, const char *mess)
{
    ctx->timer = timer;
    ctx->period = period;
    strcpy(ctx->mess, mess);
    Serial.begin(9600); // initialisation du débit de la liaison série
}

void step_mess(ctx_mess_t *ctx)
{
    if (!(waitFor(ctx->timer, ctx->period)))
        return;                // sort s'il y a moins d'une période écoulée
    Serial.println(ctx->mess); // affichage du message
}

//--------- déclaration des contextes de tâches

ctx_led_t Led1;
ctx_mess_t Mess1;
ctx_timer_t Timer_led;
int cpt = 0;

//--------- Setup et Loop

void setup()
{
    //Serial.begin(115200);

    // Connect to WiFi
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nConnected to WiFi");
    // Connect to Mosquitto Server and register callback function
    client.setServer(mqttServer, mqttPort);
    client.setCallback(callback);

    while (!client.connected())
    {
        client.loop();
        Serial.print("Connecting to MQTT...");
        if (client.connect("ESP32Subscriber"))
        {
            Serial.println("connected");
            client.subscribe(mqttTopic);
        }
        else
        {
            Serial.print("failed, rc=");
            Serial.print(client.state());
            delay(2000);
        }
    }
    pinMode(BUTTON_PIN, INPUT_PULLUP);
    init_led(&Led1, 0, 100000, LED_BUILTIN);  // led exec toutes les 100ms
    init_mess(&Mess1, 1, 1000000, "bonjour"); // mess exec toutes les secondes
    setupoled();
    init_lum(&Timer_led, 2, 500000);
    pinMode(17, OUTPUT);
    ledcSetup(0, 2000, 8); //
    ledcAttachPin(17, 0);  //
}



void loop()
{
    coupe_led(&mb_interupt);
    cpt++;
    lum(&Timer_led, &mb_photo, &mb_led);
    step_led(&Led1, &mb_led, &mb_interupt);
    step_mess(&Mess1);
    oled(&mb_photo); // Draw characters of the default font
    step_bouton_musique(&mb_son);
    if (musiqueChargee)
    {
        joue_son(partition, temps, &mb_son);
    }
    client.loop();
}