"""
CSV Dimension Parser
Parses rudder stock dimension CSV files and returns structured data
Compatible with existing stock_builder_core and wedge_cutout_calc modules
Updated to support cleaner, more readable CSV format
"""
import csv
import json
from pathlib import Path


class CSVDimensionParser:
    """Parse CSV files containing rudder stock dimensions"""
    
    def __init__(self):
        self.dimensions = {}
        self._in_overview = False
        self._in_posts = False
        self._in_tines = False
    
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
                'style': str,
                'cutout_mm': float,
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
                        'type': 'wedge', 'plate', 'cylinder', or 'none',
                        'start': float,
                        'width': float (for wedge/plate),
                        'diameter': float (for cylinder),
                        'length': float,
                        'plate_thickness': float (if wedge/plate),
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
                # Skip empty rows
                if not row:
                    continue
                
                # Skip comment lines (starting with #)
                if row[0].strip().startswith('#'):
                    # Check for section headers in comments
                    line = row[0].upper()
                    if 'OVERVIEW' in line:
                        self._in_overview = True
                        self._in_posts = False
                        self._in_tines = False
                    elif 'POST SECTIONS' in line:
                        self._in_overview = False
                        self._in_posts = True
                        self._in_tines = False
                    elif 'TINE ATTACHMENTS' in line:
                        self._in_overview = False
                        self._in_posts = False
                        self._in_tines = True
                    continue
                
                # Parse data rows
                self._parse_row(row)
        
        return self.dimensions
    
    def _parse_row(self, row):
        """Parse a single CSV row based on current section context"""
        # Check if row starts with a known type prefix (for backward compatibility)
        row_type = row[0].lower().strip()
        
        # Handle explicit row types (backward compatibility)
        if row_type == 'meta':
            self._parse_meta_row(row)
        elif row_type == 'post':
            self._parse_post_row(row)
        elif row_type == 'tine':
            self._parse_tine_row(row)
        # Handle new format based on section context
        elif self._in_overview:
            self._parse_overview_row(row)
        elif self._in_posts:
            # In new format, posts section doesn't have 'post' prefix
            # but we'll handle both formats
            if row_type != 'post':
                # Insert 'post' at beginning for consistent processing
                row.insert(0, 'post')
            self._parse_post_row(row)
        elif self._in_tines:
            # Similar handling for tines
            if row_type != 'tine':
                row.insert(0, 'tine')
            self._parse_tine_row(row)
    
    def _parse_overview_row(self, row):
        """Parse overview row in new format: key,value"""
        if len(row) >= 2:
            key = row[0].strip()
            value = row[1].strip()
            
            # Skip if this looks like a header row
            if key.lower() in ['boat_name', 'version', 'style', 'cutout_mm']:
                if value.lower() in ['version', 'style', 'cutout_mm']:
                    return  # This is a header, skip it
            
            # Store the key-value pair
            if key == 'boat_name':
                self.dimensions['boat_name'] = value
            elif key == 'version':
                self.dimensions['version'] = value
            elif key == 'style':
                self.dimensions['style'] = value
            elif key == 'cutout_mm':
                self.dimensions['cutout_mm'] = float(value)
    
    def _parse_meta_row(self, row):
        """Parse metadata row in old format: meta,boat_name,version,style,cutout_mm"""
        if len(row) >= 3:
            # Skip header row
            if row[1] == 'boat_name' and row[2] == 'version':
                return
                
            # Parse actual meta data - all values after 'meta' tag
            if len(row) >= 5:
                self.dimensions['boat_name'] = row[1].strip()
                self.dimensions['version'] = row[2].strip()
                self.dimensions['style'] = row[3].strip()
                self.dimensions['cutout_mm'] = float(row[4].strip())
            elif len(row) >= 4:
                self.dimensions['boat_name'] = row[1].strip()
                self.dimensions['version'] = row[2].strip()
                self.dimensions['style'] = row[3].strip()
                # Default cutout if not specified
                self.dimensions['cutout_mm'] = 2.0
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
        if row[1] in ['type', 'Type'] or (len(row) > 2 and row[2] in ['start', 'Start']):
            return
            
        post = {
            'type': row[1].strip(),
            'start': float(row[2]),
            'end': float(row[3]),
            'diameter_start': float(row[4]),
            'label': row[-1].strip()  # Label is always last
        }
        
        # For taper type, include diameter_end
        if post['type'] == 'taper':
            if len(row) >= 7 and row[5].strip():  # Check if diameter_end exists and is not empty
                post['diameter_end'] = float(row[5])
            else:
                # For taper without diameter_end, this might be an error
                # but we'll handle it gracefully
                post['diameter_end'] = post['diameter_start']
        elif post['type'] == 'cylinder':
            # For cylinder, diameter_end equals diameter_start
            post['diameter_end'] = post['diameter_start']
        
        self.dimensions['posts'].append(post)
    
    def _parse_tine_row(self, row):
        """Parse tine row based on type:
        - none: tine,none
        - wedge: tine,wedge,start,width,length,plate_thickness,angle,label
        - plate: tine,plate,start,width,length,plate_thickness,angle,label
        - cylinder: tine,cylinder,start,diameter,length,angle,label
        - tang (legacy): tine,tang,start,width,length,angle,label
        """
        if len(row) < 2:
            return
        
        # Skip header rows
        if row[1] in ['type', 'Type', 'wedge', 'plate'] and len(row) > 2 and row[2] in ['start', 'Start']:
            return
        
        tine_type = row[1].strip().lower()
        
        if tine_type == 'none':
            # No-op tine
            tine = {
                'type': 'none',
                'start': 0,
                'width': 0,
                'length': 0,
                'angle': 0,
                'label': 'None'
            }
        elif tine_type in ['wedge', 'plate']:
            if len(row) < 8:
                return
            tine = {
                'type': tine_type,
                'start': float(row[2]),
                'width': float(row[3]),
                'length': float(row[4]),
                'plate_thickness': float(row[5]),
                'angle': float(row[6]),
                'label': row[7].strip()
            }
        elif tine_type == 'cylinder':
            if len(row) < 7:
                return
            tine = {
                'type': 'cylinder',
                'start': float(row[2]),
                'diameter': float(row[3]),  # Note: diameter, not width
                'length': float(row[4]),
                'angle': float(row[5]),
                'label': row[6].strip()
            }
            # For compatibility, also store diameter as width
            tine['width'] = tine['diameter']
        elif tine_type == 'tang':
            # Legacy tang type support
            if len(row) < 7:
                return
            tine = {
                'type': 'tang',
                'start': float(row[2]),
                'width': float(row[3]),
                'length': float(row[4]),
                'angle': float(row[5]),
                'label': row[6].strip()
            }
        else:
            # Unknown tine type, skip
            return
        
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
            tine_type = tine.get('type')
            
            if tine_type == 'none':
                continue  # No validation needed for none type
            
            required = ['type', 'start', 'length', 'angle']
            for field in required:
                if field not in tine:
                    errors.append(f"Tine {i} missing field: {field}")
            
            # Type-specific validation
            if tine_type in ['wedge', 'plate']:
                if 'width' not in tine:
                    errors.append(f"{tine_type.capitalize()} tine {i} missing width")
                if 'plate_thickness' not in tine:
                    errors.append(f"{tine_type.capitalize()} tine {i} missing plate_thickness")
            elif tine_type == 'cylinder':
                if 'diameter' not in tine and 'width' not in tine:
                    errors.append(f"Cylinder tine {i} missing diameter")
            elif tine_type == 'tang':
                if 'width' not in tine:
                    errors.append(f"Tang tine {i} missing width")
        
        return (len(errors) == 0, errors)
    
    def has_wedges(self):
        """Check if the stock has wedge-type tines"""
        return any(tine.get('type') == 'wedge' for tine in self.dimensions.get('tines', []))
    
    def has_plates(self):
        """Check if the stock has plate-type tines"""
        return any(tine.get('type') == 'plate' for tine in self.dimensions.get('tines', []))
    
    def has_cylinders(self):
        """Check if the stock has cylinder-type tines"""
        return any(tine.get('type') == 'cylinder' for tine in self.dimensions.get('tines', []))
    
    def has_tangs(self):
        """Check if the stock has tang-type tines (legacy)"""
        return any(tine.get('type') == 'tang' for tine in self.dimensions.get('tines', []))
    
    def get_stock_style(self):
        """
        Get the stock style based on tine types or explicit style meta field
        
        Returns:
            Style from meta field if present, otherwise:
            'wedge', 'plate', 'cylinder', 'tang', 'mixed', or 'none' based on tine types
        """
        # If style is explicitly specified in meta, use that
        if 'style' in self.dimensions:
            return self.dimensions['style']
        
        # Otherwise, determine from tine types
        has_wedges = self.has_wedges()
        has_plates = self.has_plates()
        has_cylinders = self.has_cylinders()
        has_tangs = self.has_tangs()
        
        type_count = sum([has_wedges, has_plates, has_cylinders, has_tangs])
        
        if type_count > 1:
            return 'mixed'
        elif has_wedges:
            return 'wedge'
        elif has_plates:
            return 'plate'
        elif has_cylinders:
            return 'cylinder'
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