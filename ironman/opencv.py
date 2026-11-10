import mediapipe as mp
import cv2
import pygame
import math
import random

# Scherm instellingen
WIDTH, HEIGHT = 1700, 700

# Kleuren
black, white = (0, 0, 0), (255, 255, 255)
cyan, yellow, magenta = (0, 255, 255), (255, 255, 0), (255, 0, 255)
red, green, blue, orange = (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 165, 0)


# Setup pygame/mediapipe
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Ironman Hand Tracker")
clock = pygame.time.Clock()

mp_hands = mp.solutions.hands
hands = mp_hands.Hands()
mp_draw = mp.solutions.drawing_utils

camera = cv2.VideoCapture(0)

# De sprite class
class MijnSprite(pygame.sprite.Sprite):
    def __init__(self, color, width, height):
        super().__init__()
        self.image = pygame.Surface([width, height])
        self.image.fill(color)
        self.rect = self.image.get_rect()

ROOD = (255, 0, 0)

mijn_sprite = MijnSprite(cyan, 40, 40)
mijn_sprite.rect.x = 400
mijn_sprite.rect.y = 300

alle_sprites = pygame.sprite.Group()
pieces = pygame.sprite.Group()
alle_sprites.add(mijn_sprite)

# default positie
x, y = 0, 0
count = 0
fall_timer = 0 # Timer voor het vallen
show_grid = True # Of het raster zichtbaar is

# Stabiliteit voor vuist-detectie
vuistmodus = False # Stabiele status
fist_frames = 0    # Teller voor vuist
hand_frames = 0    # Teller voor hand
THRESHOLD_FRAMES = 2 # Hoeveel frames achter elkaar moet het stabiel zijn?

# Game state spul
score = 0
highscore = 0
game_over = False
base_fall_speed = 30 
last_hand_y = 0      

# Highscore laden
try:
    with open("highscore.txt", "r") as f:
        highscore = int(f.read())
except:
    highscore = 0

def save_highscore():
    global highscore
    if score > highscore:
        highscore = score
        with open("highscore.txt", "w") as f:
            f.write(str(highscore))

def reset_game():
    global raster_array, score, game_over, huidig_stuk, alle_sprites
    raster_array = [[0 for _ in range(AANTAL_X)] for _ in range(AANTAL_Y)]
    score = 0
    game_over = False
    alle_sprites.empty()
    # Voeg de debug sprite eventueel weer toe als je die wilt
    huidig_stuk = Stuk("random", 0, 10)

# Raster instellingen
AANTAL_X, AANTAL_Y = 30, 30
xas, yas = WIDTH // AANTAL_X, HEIGHT // AANTAL_Y
raster_array = [[0 for _ in range(AANTAL_X)] for _ in range(AANTAL_Y)]

# De verschillende blokjes
blok_patronen = {
    1: [
        [1, 1, 1, 1],
        [0, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 1, 0, 0]
    ],
    2: [
        [1, 1, 0, 0],
        [1, 1, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0]
    ],
    3: [
        [1, 1, 1, 0],
        [1, 0, 0, 0],
        [1, 0, 0, 0],
        [0, 0, 0, 0]
    ],

}

class Blokje(pygame.sprite.Sprite):
    def __init__(self, rij, kolom, color):
        super().__init__()
        self.color = color
        self.image = pygame.Surface((xas, yas))
        self.image.fill(self.color)
        self.rect = self.image.get_rect()
        
        # Bereken de positie op basis van de array index
        self.rect.x = kolom * xas
        self.rect.y = rij * yas

class Stuk:
    def __init__(self, patroon_id, start_rij, start_kolom):
        self.blokjes = []
        self.rect = pygame.Rect(start_kolom * xas, start_rij * yas, 0, 0)
        self.is_alive = True # Is het stuk succesvol geplaatst?
        
        # Kies één kleur voor de hele piece
        self.color = random.choice([red, green, blue, yellow, magenta, orange])
        
        if patroon_id == "random":
            patroon_id = random.choice(list(blok_patronen.keys()))
            
        patroon = blok_patronen[patroon_id]
        
        # Check of spawnplek vrij is
        for r, rij_data in enumerate(patroon):
            for k, waarde in enumerate(rij_data):
                if waarde == 1:
                    grid_r = start_rij + r
                    grid_k = start_kolom + k
                    # Als de plek in de array al bezet is (niet 0)
                    if 0 <= grid_r < AANTAL_Y and 0 <= grid_k < AANTAL_X:
                        if raster_array[grid_r][grid_k] != 0:
                            print("Geen ruimte!")
                            self.is_alive = False
                            return
        
        # Alleen blokjes maken als de plek vrij was
        for r, rij_data in enumerate(patroon):
            for k, waarde in enumerate(rij_data):
                if waarde == 1:
                    nieuw_blokje = Blokje(start_rij + r, start_kolom + k, self.color)
                    self.blokjes.append(nieuw_blokje)
                    alle_sprites.add(nieuw_blokje)
        
        if self.blokjes:
            self.rect = self.blokjes[0].rect.unionall([b.rect for b in self.blokjes[1:]])

    def val(self, pixels):
        can_fall = True
        for b in self.blokjes:
            curr_k = b.rect.x // xas
            curr_r = b.rect.y // yas
            next_r = curr_r + 1
            
            if b.rect.y + pixels + b.rect.height > HEIGHT:
                can_fall = False
                break
            
            if next_r < AANTAL_Y and 0 <= curr_k < AANTAL_X:
                if raster_array[next_r][curr_k] != 0:
                    can_fall = False
                    break
        
        if can_fall:
            self.rect.y += pixels
            for b in self.blokjes:
                b.rect.y += pixels
            return False 
        else:
            for b in self.blokjes:
                r = b.rect.y // yas
                k = b.rect.x // xas
                if 0 <= r < AANTAL_Y and 0 <= k < AANTAL_X:
                    raster_array[r][k] = 1 
                alle_sprites.remove(b)
            
            self.clear_rows()
            return True 

    def clear_rows(self):
        global raster_array, score
        nieuwe_array = [rij for rij in raster_array if 0 in rij]
        aantal_verwijderd = AANTAL_Y - len(nieuwe_array)
        
        if aantal_verwijderd > 0:
            score += aantal_verwijderd * 100
            save_highscore()
            
        for _ in range(aantal_verwijderd):
            nieuwe_array.insert(0, [0 for _ in range(AANTAL_X)])
        
        raster_array = nieuwe_array

    def rotate(self):
        if not self.blokjes: return
        
        # Gebruik het eerste blokje als middelpunt voor de rotatie
        anker_x = self.blokjes[0].rect.x
        anker_y = self.blokjes[0].rect.y
        
        nieuwe_posities = []
        for b in self.blokjes:
            # Bereken relatieve positie t.o.v. het anker
            rel_x = (b.rect.x - anker_x) // xas
            rel_y = (b.rect.y - anker_y) // yas
            
            # Roteer 90 graden: (x, y) -> (-y, x)
            nieuw_rel_x = -rel_y
            nieuw_rel_y = rel_x
            
            nieuw_x = anker_x + nieuw_rel_x * xas
            nieuw_y = anker_y + nieuw_rel_y * yas
            
            # Check of de nieuwe plek geldig is
            grid_k = nieuw_x // xas
            grid_r = nieuw_y // yas
            
            if grid_k < 0 or grid_k >= AANTAL_X or grid_r < 0 or grid_r >= AANTAL_Y:
                return # Kan niet draaien: buiten beeld
            if raster_array[grid_r][grid_k] != 0:
                return # Kan niet draaien: botst met ander blokje
                
            nieuwe_posities.append((nieuw_x, nieuw_y))
            
        # Als alle blokjes geldig kunnen draaien, voer de rotatie uit
        for i, b in enumerate(self.blokjes):
            b.rect.x, b.rect.y = nieuwe_posities[i]
        
        # Update de totale rect van de piece
        self.rect = self.blokjes[0].rect.unionall([b.rect for b in self.blokjes[1:]])

    def hard_drop(self):
        # Laat het blokje vallen tot het niet meer kan
        landed = False
        while not landed:
            landed = self.val(yas)
        return True

    def checkomgeving(self, dx):
        # Controleert of de plek (huidige + dx) vrij is in de array
        for b in self.blokjes:
            new_k = (b.rect.x // xas) + dx
            curr_r = b.rect.y // yas
            
            if new_k < 0 or new_k >= AANTAL_X:
                return False
            
            if 0 <= curr_r < AANTAL_Y:
                if raster_array[curr_r][new_k] != 0:
                    return False
        return True

    def movepiece(self, x_verschil):
        # Richting bepalen op basis van x_verschil
        # Geen cooldown meer: beweegt elke frame dat de hand opzij staat
        dir_x = 0
        if x_verschil > 100: 
            dir_x = 1 # Naar rechts
        elif x_verschil < -100: 
            dir_x = -1 # Naar links
        
        if dir_x != 0:
            # Gebruik checkomgeving om te kijken of we mogen bewegen
            if self.checkomgeving(dir_x):
                self.rect.x += dir_x * xas
                for b in self.blokjes:
                    b.rect.x += dir_x * xas

# Nieuw stuk aanmaken
huidig_stuk = Stuk("random", 0, 10)





# Game loop
while True:
    # Events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            camera.release()
            pygame.quit()
            exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_g:
                show_grid = not show_grid
            if event.key == pygame.K_SPACE and not game_over:
                huidig_stuk.rotate()
            if event.key == pygame.K_r and game_over:
                reset_game()

    fall_timer += 1
    
    # Bereken dynamische snelheid (hoe hoger de score, hoe sneller)
    # Begint bij 30, gaat naar beneden (sneller) per 500 punten
    huidige_snelheid = max(2, base_fall_speed - (score // 500) * 5)

    # Alleen vallen als het huidige stuk 'leeft' en het spel niet voorbij is
    if not game_over:
        if huidig_stuk.is_alive:
            if fall_timer > huidige_snelheid:
                # Check of het stuk landt
                landed = huidig_stuk.val(yas)
                if landed:
                    huidig_stuk = Stuk("random", 0, 10)
                fall_timer = 0
        else:
            # Als het nieuwe stuk niet geplaatst kan worden -> GAME OVER
            game_over = True
            save_highscore()

    success, frame = camera.read()
    if not success or frame is None:
        continue

    frame = cv2.flip(frame, 1)

    rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_image)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS
            )

            # Bereken het middelpunt van de hele hand/vuist (gemiddelde van alle landmarks)
            all_lms = hand_landmarks.landmark
            x_midden = sum([lm.x for lm in all_lms]) / 21
            y_midden = sum([lm.y for lm in all_lms]) / 21
            x = int(x_midden * WIDTH)
            y = int(y_midden * HEIGHT)

            # Afstand tot het MIDDEN van de huidige piece (X en Y)
            dist1 = math.dist((x, y), huidig_stuk.rect.center)
            
            # Interactie: beweeg het stuk als je een vuist maakt
            if dist1 < 500 and vuistmodus and not game_over:
                x_verschil = x - huidig_stuk.rect.centerx
                huidig_stuk.movepiece(x_verschil)
            
            # HARD DROP: Platte hand krachtig naar beneden bewegen
            if not vuistmodus and not game_over:
                dy = y - last_hand_y
                if dy > 150: # VEEL HOGERE DREMPEL: Alleen bij krachtige beweging
                    if huidig_stuk.hard_drop():
                        huidig_stuk = Stuk("random", 0, 10)
            
            last_hand_y = y

            # Vuist detectie
            gekrulde_vingers = 0
            for tip_idx, knokkel_idx in [(8, 6), (12, 10), (16, 14), (20, 18)]:
                if hand_landmarks.landmark[tip_idx].y > hand_landmarks.landmark[knokkel_idx].y:
                    gekrulde_vingers += 1
            
            is_nu_vuist = (gekrulde_vingers >= 3)

            if is_nu_vuist:
                fist_frames += 1
                hand_frames = 0
            else:
                hand_frames += 1
                fist_frames = 0

            if not vuistmodus and fist_frames >= THRESHOLD_FRAMES:
                vuistmodus = True
                print("Status: vuist")
            
            if vuistmodus and hand_frames >= THRESHOLD_FRAMES:
                vuistmodus = False
                print("Status: hand")

    # cv2 → pygame
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame_surface = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
    frame_surface = pygame.transform.scale(frame_surface, (WIDTH, HEIGHT))

    screen.blit(frame_surface, (0, 0))

    # Teken de gelande blokjes uit de array
    for r in range(AANTAL_Y):
        for k in range(AANTAL_X):
            if raster_array[r][k] != 0:
                pygame.draw.rect(screen, white, (k * xas, r * yas, xas, yas))

    alle_sprites.draw(screen)

    # UI tekenen
    font = pygame.font.SysFont("Arial", 40, bold=True)
    score_surf = font.render(f"SCORE: {score}", True, white)
    high_surf = font.render(f"HIGH SCORE: {highscore}", True, yellow)
    screen.blit(score_surf, (20, 20))
    screen.blit(high_surf, (20, 70))

    # Game over scherm
    if game_over:
        # Donkere overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        
        msg_font = pygame.font.SysFont("Arial", 80, bold=True)
        sub_font = pygame.font.SysFont("Arial", 40)
        
        go_surf = msg_font.render("GAME OVER", True, red)
        restart_surf = sub_font.render("Druk op 'R' om opnieuw te starten", True, white)
        
        screen.blit(go_surf, (WIDTH//2 - go_surf.get_width()//2, HEIGHT//2 - 100))
        screen.blit(restart_surf, (WIDTH//2 - restart_surf.get_width()//2, HEIGHT//2 + 20))

    # Raster
    if show_grid:
        for x_positie in range(0, WIDTH, xas):
            pygame.draw.line(screen, (255, 255, 0), (x_positie, 0), (x_positie, HEIGHT), 2)
        
        for y_positie in range(0, HEIGHT, yas):
            pygame.draw.line(screen, (255, 255, 0), (0, y_positie), (WIDTH, y_positie), 2)

    # collision
    distance = math.dist(
        (x, y),
        (mijn_sprite.rect.x, mijn_sprite.rect.y)
    )

    if distance < 50:
        count += 1
        # print(f"💥 botsing! Totaal: {count}")

    pygame.display.flip()
    clock.tick(30)