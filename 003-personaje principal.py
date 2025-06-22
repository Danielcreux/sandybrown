import cv2
import numpy as np
import random
import math
import mysql.connector
from mysql.connector import Error
from enum import Enum
import time

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'sandybrown',
    'user': 'sandybrown',
    'password': 'sandybrown'
}

# NPC Behavior States
class NPCState(Enum):
    WANDERING = 1
    WORKING = 2
    SOCIALIZING = 3
    RESTING = 4

class Character:
    def __init__(self, x, y, color, speed=5, size=20):
        self.x = x
        self.y = y
        self.color = color
        self.speed = speed
        self.size = size
        self.direction = 0  # Angle in radians
    
    def move(self, dx, dy):
        self.x += dx * self.speed
        self.y += dy * self.speed

class NPC(Character):
    def __init__(self, x, y, npc_id, name, color=None):
        color = color or (random.randint(50, 200), random.randint(50, 200), random.randint(50, 200))
        super().__init__(x, y, color, speed=random.uniform(1.0, 3.0))
        self.id = npc_id
        self.name = name
        self.state = NPCState.WANDERING
        self.target_x = None
        self.target_y = None
        self.state_timer = 0
        self.change_state()
    
    def change_state(self):
        self.state = random.choice(list(NPCState))
        self.state_timer = random.randint(60, 180)  # 1-3 seconds at 60 FPS
        
        if self.state == NPCState.WORKING:
            self.target_x = random.randint(100, 700)
            self.target_y = random.randint(100, 500)
        else:
            self.target_x = None
            self.target_y = None
    
    def update(self, npcs, world_width, world_height):
        self.state_timer -= 1
        if self.state_timer <= 0:
            self.change_state()
        
        if self.state == NPCState.WANDERING:
            if random.random() < 0.02:
                self.direction = random.uniform(0, 2 * math.pi)
            self.x += math.cos(self.direction) * self.speed
            self.y += math.sin(self.direction) * self.speed
        
        elif self.state == NPCState.WORKING and self.target_x:
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > 5:
                self.direction = math.atan2(dy, dx)
                self.x += math.cos(self.direction) * self.speed
                self.y += math.sin(self.direction) * self.speed
        
        self.x = max(0, min(world_width, self.x))
        self.y = max(0, min(world_height, self.y))

class GameWorld:
    def __init__(self, width=800, height=600):
        self.width = width
        self.height = height
        self.world_img = np.ones((height, width, 3), dtype=np.uint8) * 30
        self.player = Character(width//2, height//2, (0, 100, 255), 5, 15)
        self.npcs = []
        self.next_npc_id = 1
        self.db_connection = None
        self.mouse_pos = (0, 0)  # Initialize mouse position
        
        self.setup_database()
        self.load_npcs_from_db()
        if not self.npcs:
            self.create_initial_npcs(5)
        
        # Set up mouse callback
        cv2.namedWindow('NPC Simulation')
        cv2.setMouseCallback('NPC Simulation', self.update_mouse_pos)
        
    def update_mouse_pos(self, event, x, y, flags, param):
        """Update mouse position whenever it moves"""
        self.mouse_pos = (x, y)

            
    
    def setup_database(self):
        try:
            self.db_connection = mysql.connector.connect(**DB_CONFIG)
            cursor = self.db_connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS npc (
                    Identificador INT PRIMARY KEY,
                    x FLOAT(255,10) NOT NULL,
                    y FLOAT(255,10) NOT NULL,
                    nombre VARCHAR(255) NOT NULL,
                    direccion FLOAT(10,10) NOT NULL,
                    velocidad FLOAT(10,10) NOT NULL,
                    state INT NOT NULL
                ) ENGINE=MEMORY DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
            """)
            self.db_connection.commit()
        except Error as e:
            print(f"Database error: {e}")
    
    def load_npcs_from_db(self):
        if not self.db_connection:
            return
        
        try:
            cursor = self.db_connection.cursor(dictionary=True)  # This is correct inside a method
            cursor.execute("SELECT * FROM npc")
            for record in cursor.fetchall():
                npc = NPC(record['x'], record['y'], record['Identificador'], record['nombre'])
                npc.direction = record['direccion']
                npc.speed = record['velocidad']
                npc.state = NPCState(record['state'])
                self.npcs.append(npc)
                if record['Identificador'] >= self.next_npc_id:
                    self.next_npc_id = record['Identificador'] + 1
        except Error as e:
            print(f"Error loading NPCs: {e}")
    def save_npcs_to_db(self):
        if not self.db_connection:
            return
        
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("DELETE FROM npc")
            for npc in self.npcs:
                cursor.execute("""
                    INSERT INTO npc (Identificador, x, y, nombre, direccion, velocidad, state)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (npc.id, npc.x, npc.y, npc.name, npc.direction, npc.speed, npc.state.value))
            self.db_connection.commit()
        except Error as e:
            print(f"Error saving NPCs: {e}")
    
    def create_initial_npcs(self, count):
        names = ["Warrior", "Mage", "Blacksmith", "Merchant", "Guard"]
        for i in range(count):
            name = f"{random.choice(names)}_{i+1}"
            npc = NPC(random.randint(50, self.width-50), random.randint(50, self.height-50), self.next_npc_id, name)
            self.npcs.append(npc)
            self.next_npc_id += 1
        self.save_npcs_to_db()
    
    def update(self):
        """Update game state"""
        for npc in self.npcs:
            npc.update(self.npcs, self.width, self.height)
        
        # Get current mouse position and update player direction
        mouse_x, mouse_y = self.mouse_pos
        self.player.direction = math.atan2(mouse_y - self.player.y,
                                         mouse_x - self.player.x)
    
    def draw(self):
        img = self.world_img.copy()
        
        # Draw grid
        for x in range(0, self.width, 50):
            cv2.line(img, (x, 0), (x, self.height), (50, 50, 60), 1)
        for y in range(0, self.height, 50):
            cv2.line(img, (0, y), (self.width, y), (50, 50, 60), 1)
        
        # Draw NPCs
        for npc in self.npcs:
            center = (int(npc.x), int(npc.y))
            cv2.circle(img, center, npc.size, npc.color, -1)
            cv2.circle(img, center, npc.size, (0, 0, 0), 1)
            end_point = (int(npc.x + npc.size * 1.5 * math.cos(npc.direction)), 
                         int(npc.y + npc.size * 1.5 * math.sin(npc.direction)))
            cv2.line(img, center, end_point, (0, 0, 0), 2)
            cv2.putText(img, f"{npc.name}: {npc.state.name}", 
                       (center[0] - 50, center[1] - npc.size - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # Draw player
        player_center = (int(self.player.x), int(self.player.y))
        cv2.circle(img, player_center, self.player.size, self.player.color, -1)
        cv2.circle(img, player_center, self.player.size, (0, 0, 0), 1)
        player_end = (int(self.player.x + self.player.size * 1.5 * math.cos(self.player.direction)), 
                     int(self.player.y + self.player.size * 1.5 * math.sin(self.player.direction)))
        cv2.line(img, player_center, player_end, (255, 255, 255), 2)
        
        # Draw UI
        cv2.putText(img, f"NPCs: {len(self.npcs)}", (10, 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(img, "WASD: Move | Mouse: Look | A: Add NPC | D: Remove NPC | ESC: Quit", 
                   (10, self.height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        cv2.imshow('NPC Simulation', img)
    
    def run(self):
        print("Starting simulation. Controls:")
        print("WASD: Move player")
        print("Mouse: Look direction")
        print("A: Add NPC")
        print("D: Remove NPC")
        print("ESC: Quit")
        
        last_save_time = time.time()
        
        while True:
            # Handle keyboard input
            key = cv2.waitKey(30)
            if key == 27:  # ESC
                break
            elif key == ord('a'):
                self.create_initial_npcs(1)
            elif key == ord('d') and self.npcs:
                removed = self.npcs.pop()
                print(f"Removed NPC: {removed.name}")
                self.save_npcs_to_db()
            
            # Player movement
            keys = cv2.waitKeyEx(30)
            dx, dy = 0, 0
            if keys == ord('a') or keys == 2424832:  # Left arrow
                dx = -1
            if keys == ord('d') or keys == 2555904:  # Right arrow
                dx = 1
            if keys == ord('w') or keys == 2490368:  # Up arrow
                dy = -1
            if keys == ord('s') or keys == 2621440:  # Down arrow
                dy = 1
            
            if dx != 0 and dy != 0:
                dx *= 0.7071
                dy *= 0.7071
            
            self.player.move(dx, dy)
            
            self.update()
            self.draw()
            
            # Auto-save every 5 seconds
            if time.time() - last_save_time > 5:
                self.save_npcs_to_db()
                last_save_time = time.time()
        
        if self.db_connection:
            self.db_connection.close()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    game = GameWorld(1000, 800)
    game.run()

