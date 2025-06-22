import numpy as np
import cv2
import random
import math
from dataclasses import dataclass

@dataclass
class NPC:
    id: int
    x: float
    y: float
    name: str
    direction: float  # in radians (0 to 2π)
    speed: float
    color: tuple = (0, 0, 0)  # BGR color
    
    def move(self, world_width, world_height):
        # Calculate new position based on direction and speed
        self.x += math.cos(self.direction) * self.speed
        self.y += math.sin(self.direction) * self.speed
        
        # Boundary checking - bounce off walls
        if self.x < 0 or self.x > world_width:
            self.direction = math.pi - self.direction
            self.x = np.clip(self.x, 0, world_width)
        if self.y < 0 or self.y > world_height:
            self.direction = -self.direction
            self.y = np.clip(self.y, 0, world_height)
        
        # Random direction changes (10% chance)
        if random.random() < 0.1:
            self.direction += random.uniform(-0.5, 0.5)
            self.direction %= 2 * math.pi

class NPCSimulator:
    def __init__(self, width=800, height=600):
        self.width = width
        self.height = height
        self.npcs = []
        self.world_img = np.ones((height, width, 3), dtype=np.uint8) * 255
        self.next_id = 1
    
    def create_npc(self, name, x=None, y=None, direction=None, speed=None):
        """Create a new NPC with random or specified parameters"""
        x = x if x is not None else random.uniform(0, self.width)
        y = y if y is not None else random.uniform(0, self.height)
        direction = direction if direction is not None else random.uniform(0, 2 * math.pi)
        speed = speed if speed is not None else random.uniform(0.5, 3.0)
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        
        npc = NPC(
            id=self.next_id,
            x=x,
            y=y,
            name=name,
            direction=direction,
            speed=speed,
            color=color
        )
        self.npcs.append(npc)
        self.next_id += 1
        return npc
    
    def create_npc_set(self, count=10):
        """Create a set of NPCs with random parameters"""
        names = ["Warrior", "Mage", "Rogue", "Merchant", "Guard", 
                "Peasant", "King", "Queen", "Blacksmith", "Bard"]
        for i in range(count):
            name = f"{random.choice(names)}_{i}"
            self.create_npc(name)
    
    def update(self):
        """Update all NPC positions"""
        for npc in self.npcs:
            npc.move(self.width, self.height)
    
    def draw(self):
        """Draw the world with all NPCs"""
        img = self.world_img.copy()
        
        # Draw grid
        for x in range(0, self.width, 50):
            cv2.line(img, (x, 0), (x, self.height), (220, 220, 220), 1)
        for y in range(0, self.height, 50):
            cv2.line(img, (0, y), (self.width, y), (220, 220, 220), 1)
        
        # Draw NPCs
        for npc in self.npcs:
            center = (int(npc.x), int(npc.y))
            
            # Draw NPC as a circle with direction indicator
            cv2.circle(img, center, 10, npc.color, -1)
            cv2.circle(img, center, 10, (0, 0, 0), 1)  # outline
            
            # Direction indicator line
            end_point = (
                int(npc.x + 15 * math.cos(npc.direction)),
                int(npc.y + 15 * math.sin(npc.direction))
            )
            cv2.line(img, center, end_point, (0, 0, 0), 2)
            
            # Draw name
            cv2.putText(img, npc.name, (center[0] + 15, center[1] + 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        
        # Display stats
        cv2.putText(img, f"NPCs: {len(self.npcs)}", (10, 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
        
        return img
    
    def run_simulation(self):
        """Main simulation loop"""
        print("Starting NPC simulation. Press 'q' to quit, 'a' to add NPC, 'd' to delete last NPC")
        
        self.create_npc_set(5)  # Initial NPCs
        
        while True:
            img = self.draw()
            cv2.imshow('NPC Simulation', img)
            
            key = cv2.waitKey(30)
            if key == ord('q'):  # Quit
                break
            elif key == ord('a'):  # Add NPC
                self.create_npc(f"New_{self.next_id}")
            elif key == ord('d') and self.npcs:  # Delete last NPC
                removed = self.npcs.pop()
                print(f"Removed NPC: {removed.name}")
            
            self.update()
        
        cv2.destroyAllWindows()

if __name__ == "__main__":
    simulator = NPCSimulator(1000, 800)
    simulator.run_simulation()
