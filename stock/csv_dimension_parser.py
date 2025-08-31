"""
CSV Dimension Parser
Parses rudder stock dimension CSV files and returns structured data
Compatible with existing stock_builder_core and wedge_cutout_calc modules
"""
import csv
import json
from pathlib import Path


class CSVDimensionParser:
    """Parse CSV files containing rudder stock dimensions"""
    
    def __init__(self):
        self.dimensions = {}
    
    def parse_csv_file(self, csv_path):
        """
        Parse a CSV file and return dimensions as a dictionary
        
        Args:
            csv_path: Path to CSV file (string or Path object)
            
        Returns:
            Dictionary matching existing code structure:
            {
                'boat_name': str,
                'version': str,
                'posts': [
                    {
                        'type': 'cylinder' or 'taper',
                        'start': float,
                        'end': float,
                        'diameter_start': float,
                        'diameter_end': float (if taper),
                        'label': str
                    },
                    ...
                ],
                'tines': [
                    {
                        'type': 'wedge' or 'tang',
                        'start': float,
                        'width': float,
                        'length': float,
                        'plate_thickness': float (if wedge),
                        'angle': float,
                        'label': str
                    },
                    ...
                ]
            }
        """
        csv_path = Path(csv_path)
        
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        # Initialize structure matching existing code
        self.dimensions = {
            'posts': [],
            'tines': []
        }
        
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or row[0].startswith('#'):
                    continue
                
                # Skip header row if it exists
                if row[0].lower() in ['type', 'section'] and 'start' in [r.lower() for r in row]:
                    continue
                    
                self._parse_row(row)
        
        return self.dimensions
    
    def _parse_row(self, row):
        """Parse a single CSV row"""
        row_type = row[0].lower()
        
        if row_type == 'meta':
            self._parse_meta_row(row)
        elif row_type == 'post':
            self._parse_post_row(row)
        elif row_type == 'tine':
            self._parse_tine_row(row)
        # Ignore other row types
    
    def _parse_meta_row(self, row):
        """Parse metadata row: meta,key,value"""
        if len(row) >= 3:
            # Skip header row
            if row[1] == 'boat_name' and row[2] == 'version':
                return
                
            # Parse actual meta data - all values after 'meta' tag
            # meta,MackenSea,1.0.0,wedge -> boat_name=MackenSea, version=1.0.0, style=wedge
            if len(row) >= 4:
                self.dimensions['boat_name'] = row[1].strip()
                self.dimensions['version'] = row[2].strip()
                self.dimensions['style'] = row[3].strip()
            elif len(row) == 3:
                # Old format with just key,value
                key = row[1].strip()
                value = row[2].strip()
                self.dimensions[key] = value
    
    def _parse_post_row(self, row):
        """Parse post row: post,type,start,end,diameter_start,[diameter_end],label"""
        if len(row) < 6:
            return
        
        # Skip header rows
        if row[1] == 'type' or row[2] == 'start':
            return
            
        post = {
            'type': row[1],
            'start': float(row[2]),
            'end': float(row[3]),
            'diameter_start': float(row[4]),
            'label': row[-1]  # Label is always last
        }
        
        # For taper type, include diameter_end
        if post['type'] == 'taper' and len(row) >= 7:
            post['diameter_end'] = float(row[5])
        elif post['type'] == 'cylinder':
            # For cylinder, diameter_end equals diameter_start (not always needed but doesn't hurt)
            post['diameter_end'] = post['diameter_start']
        
        self.dimensions['posts'].append(post)
    
    def _parse_tine_row(self, row):
        """Parse tine row: tine,type,start,width,length,[plate_thickness],angle,label"""
        if len(row) < 7:
            return
        
        # Skip header rows
        if row[1] in ['type', 'wedge', 'plate'] and row[2] == 'start':
            return
            
        tine = {
            'type': row[1],
            'start': float(row[2]),
            'width': float(row[3]),
            'length': float(row[4]),
            'label': row[-1]  # Label is always last
        }
        
        # Handle different tine types
        if tine['type'] == 'wedge':
            # Wedge has plate_thickness
            if len(row) >= 8:
                tine['plate_thickness'] = float(row[5])
                tine['angle'] = float(row[6])
            else:
                tine['angle'] = float(row[5])
                tine['plate_thickness'] = 5.0  # Default
        elif tine['type'] == 'tang':
            # Tang doesn't have plate_thickness
            tine['angle'] = float(row[5])
        
        self.dimensions['tines'].append(tine)
    
    def to_json(self, indent=2):
        """Return dimensions as formatted JSON string"""
        return json.dumps(self.dimensions, indent=indent)
    
    def validate_dimensions(self):
        """
        Validate that parsed dimensions have required fields
        
        Returns:
            Tuple (is_valid, error_messages)
        """
        errors = []
        
        # Check for required metadata
        if 'boat_name' not in self.dimensions:
            errors.append("Missing boat_name in metadata")
        
        # Check for at least one post
        if not self.dimensions.get('posts'):
            errors.append("No posts defined")
        
        # Validate post fields
        for i, post in enumerate(self.dimensions.get('posts', [])):
            required = ['type', 'start', 'end', 'diameter_start']
            for field in required:
                if field not in post:
                    errors.append(f"Post {i} missing field: {field}")
            
            if post.get('type') == 'taper' and 'diameter_end' not in post:
                errors.append(f"Taper post {i} missing diameter_end")
        
        # Validate tine fields if present
        for i, tine in enumerate(self.dimensions.get('tines', [])):
            required = ['type', 'start', 'width', 'length', 'angle']
            for field in required:
                if field not in tine:
                    errors.append(f"Tine {i} missing field: {field}")
            
            if tine.get('type') == 'wedge' and 'plate_thickness' not in tine:
                errors.append(f"Wedge tine {i} missing plate_thickness")
        
        return (len(errors) == 0, errors)
    
    def has_wedges(self):
        """Check if the stock has wedge-type tines"""
        return any(tine.get('type') == 'wedge' for tine in self.dimensions.get('tines', []))
    
    def has_tangs(self):
        """Check if the stock has tang-type tines"""
        return any(tine.get('type') == 'tang' for tine in self.dimensions.get('tines', []))
    
    def get_stock_style(self):
        """
        Get the stock style based on tine types or explicit style meta field
        
        Returns:
            Style from meta field if present, otherwise:
            'wedge', 'tang', 'mixed', or 'none' based on tine types
        """
        # If style is explicitly specified in meta, use that
        if 'style' in self.dimensions:
            return self.dimensions['style']
        
        # Otherwise, determine from tine types
        has_wedges = self.has_wedges()
        has_tangs = self.has_tangs()
        
        if has_wedges and has_tangs:
            return 'mixed'
        elif has_wedges:
            return 'wedge'
        elif has_tangs:
            return 'tang'
        else:
            return 'none'


def parse_csv_dimensions(csv_path):
    """
    Convenience function to parse CSV and return dimensions
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        Dictionary of parsed dimensions matching existing code structure
    """
    parser = CSVDimensionParser()
    return parser.parse_csv_file(csv_path)


def main():
    """Test the parser with a sample CSV"""
    import sys
    
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        # Default test path
        csv_path = Path.home() / "Rudder_Code" / "boats" / "MackenSea" / "config" / "dimensions.csv"
    
    try:
        parser = CSVDimensionParser()
        dimensions = parser.parse_csv_file(csv_path)
        
        # Validate
        is_valid, errors = parser.validate_dimensions()
        
        if is_valid:
            print("✅ CSV parsed successfully!")
            print(f"\nBoat: {dimensions.get('boat_name', 'Unknown')}")
            print(f"Version: {dimensions.get('version', 'Unknown')}")
            print(f"Posts: {len(dimensions.get('posts', []))}")
            print(f"Tines: {len(dimensions.get('tines', []))}")
            print(f"Stock Style: {parser.get_stock_style()}")
            print("\nFull dimensions:")
            print(parser.to_json())
        else:
            print("❌ Validation errors:")
            for error in errors:
                print(f"  - {error}")
            
    except Exception as e:
        print(f"❌ Error parsing CSV: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())