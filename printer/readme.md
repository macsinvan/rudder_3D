Each piece is named following the pattern:
- `MackenSea_1A.step` - First Z-slice, left piece
- `MackenSea_1B.step` - First Z-slice, right piece (if X-split needed)
- `MackenSea_2A.step` - Second Z-slice, etc.

## 3D Printing Workflow

1. **Import to Slicer**: Load all pieces into Bambu Studio or preferred slicer
2. **Print Port Half**: Print all pieces as-is
3. **Mirror for Starboard**: Mirror all pieces and print again
4. **Assembly**:
   - Use 6mm alignment pins/bolts through alignment holes
   - Insert carbon fiber stock
   - Bond pieces together with epoxy
   - Join port and starboard halves at centerline

## Troubleshooting

### Import Errors
- Ensure STEP files are in correct directories
- Check file permissions
- Validate STEP files aren't corrupted

### Boolean Operation Failures
- Check that imported shapes are valid solids
- Ensure sufficient overlap between foil and cutout
- Verify positioning parameters are correct

### Export Failures
- Check write permissions on output directory
- Ensure sufficient disk space
- Verify pieces have valid geometry

### Memory Issues
- For complex geometries, close other applications
- Consider simplifying input geometry
- Process one operation at a time

## Module Descriptions

### DemoModelBuild.py
Main orchestration script that coordinates the entire workflow from import to export.

### printer/cutting_operations.py
- `create_cutting_plan()`: Analyzes model and determines cutting strategy
- `perform_cutting_operations()`: Executes cuts to create individual pieces

### printer/stock_positioning.py
- `rotate_stock_180()`: Orients stock correctly
- `position_stock()`: Places stock at specified coordinates
- `position_stock_cutout()`: Positions cutout with clearance
- `position_all_stock_components()`: Complete positioning workflow

### helpers/step_save_load.py
- `load_step()`: Robust STEP file import with validation
- `save_step()`: Enhanced STEP export with error handling
- `validate_step_file()`: Pre-import file validation

## Error Messages

- **"STEP file not found"**: Input file missing from expected directory
- **"No valid objects to export"**: Geometry validation failed
- **"Boolean cut failed"**: Shapes don't intersect properly
- **"No meaningful intersection"**: Stock and foil don't overlap
- **"Shape is not a solid"**: Input geometry is open or invalid

## Future Enhancements

- Automatic safe zone detection for alignment holes
- Support for different printer build volumes
- GUI interface for parameter adjustment
- Automatic support generation for printing
- Assembly instruction generation
- Weight and material calculations

## License
Project-specific - consult project documentation

## Support
For issues or questions, check the project repository or contact the development team.

## Changelog

### v2.1.0 (Current)
- Integrated STEP helper module for robust file operations
- Improved error handling and validation

### v2.0.1
- Refactored stock positioning to separate module

### v2.0.0
- Major refactor with modular structure
- Extracted cutting operations

### v1.0.10
- Pieces remain in original positions after cutting

### v1.0.9
- Single half generation for slicer mirroring

### Earlier Versions
- Initial development and testing phases