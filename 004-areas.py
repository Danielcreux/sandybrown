import cv2
import numpy as np
import random
import math
import mysql.connector
from mysql.connector import Error
from enum import Enum

# Configuración de la base de datos
DB_CONFIG = {
    'host': 'localhost',
    'database': 'sandybrown',
    'user': 'sandybrown',
    'password': 'sandybrown'
}

# Enumeraciones
class AreaType(Enum):
    RESIDENCIAL = 1
    COMERCIAL = 2
    INDUSTRIAL = 3
    RECREATIVA = 4
    RURAL = 5

class NPCState(Enum):
    WANDERING = 1
    WORKING = 2
    SOCIALIZING = 3
    RESTING = 4

# Clase base Character
class Character:
    def __init__(self, x, y, color, speed=2, size=15):
        self.x = x
        self.y = y
        self.color = color
        self.speed = speed
        self.size = size
        self.direction = 0
    
    def move(self, dx, dy):
        self.x += dx * self.speed
        self.y += dy * self.speed

# Clase NPC que hereda de Character
class NPC(Character):
    def __init__(self, x, y, npc_id, name, color=None):
        color = color or (random.randint(50, 200), random.randint(50, 200), random.randint(50, 200))
        super().__init__(x, y, color, random.uniform(1.0, 3.0))
        self.id = npc_id
        self.name = name
        self.state = NPCState.WANDERING
        self.state_timer = 0
        self.work_area = None
        self.home_area = None
        self.assign_areas()
        self.change_state()
    
    def assign_areas(self):
        rand = random.random()
        if rand < 0.3:  # 30% comercial
            self.work_area = AreaType.COMERCIAL
        elif rand < 0.6:  # 30% industrial
            self.work_area = AreaType.INDUSTRIAL
        elif rand < 0.8:  # 20% recreativo
            self.work_area = AreaType.RECREATIVA
        else:  # 20% rural
            self.work_area = AreaType.RURAL
        
        self.home_area = AreaType.RESIDENCIAL if random.random() < 0.7 else AreaType.RURAL
    
    def change_state(self):
        self.state = random.choice(list(NPCState))
        self.state_timer = random.randint(60, 180)  # 1-3 segundos a 60 FPS
    
    def get_target_area(self, game_map):
        if self.state == NPCState.WORKING:
            return random.choice([a for a in game_map.areas if a['type'] == self.work_area])
        elif self.state == NPCState.RESTING:
            return random.choice([a for a in game_map.areas if a['type'] == self.home_area])
        elif self.state == NPCState.SOCIALIZING:
            return random.choice([a for a in game_map.areas if a['type'] == AreaType.RECREATIVA])
        else:
            return random.choice(game_map.areas)
    
    def update(self, npcs, game_map):
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.change_state()
        
        target_area = self.get_target_area(game_map)
        x1, y1, x2, y2 = target_area['rect']
        target_x = random.randint(x1, x2)
        target_y = random.randint(y1, y2)
        
        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist > 10:
            self.direction = math.atan2(dy, dx)
            self.x += math.cos(self.direction) * self.speed
            self.y += math.sin(self.direction) * self.speed
        
        self.x = max(0, min(game_map.width, self.x))
        self.y = max(0, min(game_map.height, self.y))

# Clase GameMap
class GameMap:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.areas = []
        self.generate_areas()
        self.map_img = self.create_map_image()
    
    def generate_areas(self):
        self.areas.append({
            'type': AreaType.RESIDENCIAL,
            'rect': (0, 0, self.width//3, self.height//2),
            'color': (70, 70, 180)
        })
        self.areas.append({
            'type': AreaType.COMERCIAL,
            'rect': (self.width//3, 0, 2*self.width//3, self.height//2),
            'color': (180, 70, 70)
        })
        self.areas.append({
            'type': AreaType.INDUSTRIAL,
            'rect': (2*self.width//3, 0, self.width, self.height//2),
            'color': (70, 180, 70)
        })
        self.areas.append({
            'type': AreaType.RECREATIVA,
            'rect': (0, self.height//2, self.width//2, self.height),
            'color': (180, 180, 70)
        })
        self.areas.append({
            'type': AreaType.RURAL,
            'rect': (self.width//2, self.height//2, self.width, self.height),
            'color': (70, 180, 180)
        })
    
    def create_map_image(self):
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        for area in self.areas:
            x1, y1, x2, y2 = area['rect']
            cv2.rectangle(img, (x1, y1), (x2, y2), area['color'], -1)
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 0), 2)
            
            text = area['type'].name
            font = cv2.FONT_HERSHEY_SIMPLEX
            text_size = cv2.getTextSize(text, font, 0.5, 1)[0]
            text_x = x1 + (x2 - x1 - text_size[0]) // 2
            text_y = y1 + (y2 - y1 + text_size[1]) // 2
            cv2.putText(img, text, (text_x, text_y), font, 0.5, (255, 255, 255), 1)
        
        cv2.line(img, (self.width//3, 0), (self.width//3, self.height), (200, 200, 200), 3)
        cv2.line(img, (2*self.width//3, 0), (2*self.width//3, self.height), (200, 200, 200), 3)
        cv2.line(img, (0, self.height//2), (self.width, self.height//2), (200, 200, 200), 3)
        return img

# Clase principal GameWorld con conexión a DB
class GameWorld:
    def __init__(self, width=1000, height=800):
        self.game_map = GameMap(width, height)
        self.player = Character(width//2, height//2, (0, 100, 255), 5, 20)
        self.npcs = []
        self.db_connection = None
        self.setup_database()
        self.load_npcs_from_db()
        if not self.npcs:
            self.create_initial_npcs(20)
        self.mouse_pos = (0, 0)
        
        cv2.namedWindow('NPC Simulation')
        cv2.setMouseCallback('NPC Simulation', self.update_mouse_pos)
    
    def setup_database(self):
        try:
            self.db_connection = mysql.connector.connect(**DB_CONFIG)
            cursor = self.db_connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS npcs (
                    id INT PRIMARY KEY,
                    x FLOAT NOT NULL,
                    y FLOAT NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    direction FLOAT NOT NULL,
                    speed FLOAT NOT NULL,
                    state INT NOT NULL,
                    work_area INT NOT NULL,
                    home_area INT NOT NULL
                )
            """)
            self.db_connection.commit()
        except Error as e:
            print(f"Database error: {e}")
    
    def load_npcs_from_db(self):
        try:
            cursor = self.db_connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM npcs")
            for record in cursor.fetchall():
                npc = NPC(record['x'], record['y'], record['id'], record['name'])
                npc.direction = record['direction']
                npc.speed = record['speed']
                npc.state = NPCState(record['state'])
                npc.work_area = AreaType(record['work_area'])
                npc.home_area = AreaType(record['home_area'])
                self.npcs.append(npc)
        except Error as e:
            print(f"Error loading NPCs: {e}")
    
    def save_npcs_to_db(self):
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("DELETE FROM npcs")
            for npc in self.npcs:
                cursor.execute("""
                    INSERT INTO npcs 
                    (id, x, y, name, direction, speed, state, work_area, home_area)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    npc.id, npc.x, npc.y, npc.name, 
                    npc.direction, npc.speed, 
                    npc.state.value, npc.work_area.value, npc.home_area.value
                ))
            self.db_connection.commit()
        except Error as e:
            print(f"Error saving NPCs: {e}")
    
    def create_initial_npcs(self, count):
        names = ["Alex", "Sam", "Taylor", "Jordan", "Casey"]
        for i in range(count):
            name = f"{random.choice(names)}_{i+1}"
            npc = NPC(
                random.randint(0, self.game_map.width),
                random.randint(0, self.game_map.height),
                i+1, name
            )
            self.npcs.append(npc)
        self.save_npcs_to_db()
    
    def update_mouse_pos(self, event, x, y, flags, param):
        self.mouse_pos = (x, y)
    
    def update(self):
        mouse_x, mouse_y = self.mouse_pos
        self.player.direction = math.atan2(mouse_y - self.player.y, mouse_x - self.player.x)
        
        for npc in self.npcs:
            npc.update(self.npcs, self.game_map)
        
        # Auto-guardado cada 5 segundos (ejemplo)
        if cv2.getTickCount() % 300 == 0:  # Aprox 5 segundos a 60 FPS
            self.save_npcs_to_db()
    
    def draw(self):
        img = self.game_map.map_img.copy()
        
        # Dibujar NPCs
        for npc in self.npcs:
            center = (int(npc.x), int(npc.y))
            cv2.circle(img, center, npc.size, npc.color, -1)
            cv2.circle(img, center, npc.size//2, (0, 0, 0), 1)
            
            # Flecha de dirección
            end_point = (
                int(npc.x + npc.size * math.cos(npc.direction)),
                int(npc.y + npc.size * math.sin(npc.direction))
            )
            cv2.arrowedLine(img, center, end_point, (0, 0, 0), 1)
        
        # Dibujar jugador
        player_center = (int(self.player.x), int(self.player.y))
        cv2.circle(img, player_center, self.player.size, self.player.color, -1)
        cv2.circle(img, player_center, self.player.size//2, (255, 255, 255), 1)
        
        # UI
        cv2.putText(img, f"NPCs: {len(self.npcs)}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.imshow('NPC Simulation', img)
    
    def handle_input(self):
        key = cv2.waitKey(30)
        dx, dy = 0, 0
        
        if key == ord('a') or key == 2424832:  # A o flecha izquierda
            dx = -1
        if key == ord('d') or key == 2555904:  # D o flecha derecha
            dx = 1
        if key == ord('w') or key == 2490368:  # W o flecha arriba
            dy = -1
        if key == ord('s') or key == 2621440:  # S o flecha abajo
            dy = 1
        
        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071
        
        self.player.move(dx, dy)
    
    def run(self):
        while True:
            self.handle_input()
            self.update()
            self.draw()
            
            if cv2.waitKey(30) == 27:  # ESC para salir
                self.save_npcs_to_db()
                if self.db_connection:
                    self.db_connection.close()
                break
        
        cv2.destroyAllWindows()

if __name__ == "__main__":
    game = GameWorld(1200, 800)
    game.run()
