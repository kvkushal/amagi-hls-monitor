import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from PIL import Image
import json
from app.config import settings
from app.models import SpriteInfo, SpriteMap

logger = logging.getLogger(__name__)


class SpriteGenerator:
    def __init__(self):
        self.sprites_dir = Path(settings.SPRITES_DIR)
        self.sprites_dir.mkdir(parents=True, exist_ok=True)
        self.grid_width = settings.SPRITE_GRID_WIDTH
        self.grid_height = settings.SPRITE_GRID_HEIGHT
        self.thumb_width = settings.THUMBNAIL_WIDTH
        self.thumb_height = settings.THUMBNAIL_HEIGHT
    
    def generate_sprite(self, stream_id: str, thumbnail_paths: List[str], 
                       timestamps: List[datetime]) -> SpriteInfo:
        """
        Combine thumbnails into a sprite sheet.
        
        Args:
            stream_id: Stream identifier
            thumbnail_paths: List of thumbnail file paths
            timestamps: Corresponding timestamps for each thumbnail
        
        Returns:
            SpriteInfo object with sprite details
        """
        if not thumbnail_paths:
            raise ValueError("No thumbnails provided for sprite generation")
        
        # Generate sprite ID
        sprite_id = f"{stream_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Calculate sprite dimensions
        sprites_per_sheet = self.grid_width * self.grid_height
        num_sprites = min(len(thumbnail_paths), sprites_per_sheet)
        
        # Calculate actual grid dimensions
        actual_cols = min(num_sprites, self.grid_width)
        actual_rows = (num_sprites + self.grid_width - 1) // self.grid_width
        
        sprite_width = actual_cols * self.thumb_width
        sprite_height = actual_rows * self.thumb_height
        
        # Create sprite image
        sprite_img = Image.new('RGB', (sprite_width, sprite_height), color='#000000')
        
        # Sprite map data
        sprite_map_data = []
        
        # Place thumbnails
        for idx, (thumb_path, timestamp) in enumerate(zip(thumbnail_paths[:num_sprites], timestamps[:num_sprites])):
            if not Path(thumb_path).exists():
                logger.warning(f"Thumbnail not found: {thumb_path}")
                continue
            
            try:
                thumb = Image.open(thumb_path)
                
                # Calculate position
                col = idx % self.grid_width
                row = idx // self.grid_width
                x = col * self.thumb_width
                y = row * self.thumb_height
                
                # Paste thumbnail
                sprite_img.paste(thumb, (x, y))
                
                # Add to sprite map
                sprite_map_data.append({
                    "timestamp": timestamp.isoformat(),
                    "x": x,
                    "y": y,
                    "w": self.thumb_width,
                    "h": self.thumb_height,
                    "index": idx
                })
                
                thumb.close()
            
            except Exception as e:
                logger.error(f"Error adding thumbnail {thumb_path} to sprite: {e}")
        
        # Save sprite image
        sprite_filename = f"{sprite_id}.jpg"
        sprite_path = self.sprites_dir / sprite_filename
        sprite_img.save(sprite_path, quality=85, optimize=True)
        sprite_img.close()
        
        # Save sprite map JSON
        sprite_map_filename = f"{sprite_id}.json"
        sprite_map_path = self.sprites_dir / sprite_map_filename
        
        sprite_map = {
            "sprite_id": sprite_id,
            "sprite_url": f"/data/sprites/{sprite_filename}",
            "grid_width": actual_cols,
            "grid_height": actual_rows,
            "thumbnail_width": self.thumb_width,
            "thumbnail_height": self.thumb_height,
            "thumbnails": sprite_map_data
        }
        
        with open(sprite_map_path, 'w') as f:
            json.dump(sprite_map, f, indent=2)
        
        logger.info(f"Sprite generated: {sprite_path} with {len(sprite_map_data)} thumbnails")
        
        # Return sprite info
        return SpriteInfo(
            sprite_id=sprite_id,
            sprite_path=str(sprite_path),
            sprite_map_path=str(sprite_map_path),
            start_timestamp=timestamps[0],
            end_timestamp=timestamps[-1],
            thumbnail_count=len(sprite_map_data),
            grid_width=actual_cols,
            grid_height=actual_rows,
            created_at=datetime.utcnow()
        )
    
    def load_sprite_map(self, sprite_id: str) -> SpriteMap:
        """Load a sprite map from JSON file."""
        sprite_map_path = self.sprites_dir / f"{sprite_id}.json"
        
        if not sprite_map_path.exists():
            raise FileNotFoundError(f"Sprite map not found: {sprite_map_path}")
        
        with open(sprite_map_path, 'r') as f:
            data = json.load(f)
        
        return SpriteMap(**data)
    
    def get_all_sprites(self, stream_id: str = None) -> List[Dict[str, Any]]:
        """Get all sprite maps, optionally filtered by stream ID."""
        sprites = []
        
        for sprite_map_path in self.sprites_dir.glob("*.json"):
            try:
                with open(sprite_map_path, 'r') as f:
                    data = json.load(f)
                
                # Filter by stream_id if provided
                if stream_id and not data.get("sprite_id", "").startswith(stream_id):
                    continue
                
                sprites.append(data)
            
            except Exception as e:
                logger.error(f"Error loading sprite map {sprite_map_path}: {e}")
        
        # Sort by creation time (newest first)
        sprites.sort(key=lambda x: x.get("sprite_id", ""), reverse=True)
        
        return sprites


# Global instance
sprite_generator = SpriteGenerator()
