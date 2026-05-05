import os
import re
import getpass
from typing import Optional

class StormConfigGenerator:
    """
    Generates storm configuration by parsing storm IDs and populating templates.
    """

    def __init__(self, storm_id: str, template_path: str, output_dir: str | None = None):
        """
        Initializes the generator, parses the storm ID, and fetches default values.
        
        Args:
            storm_id: Validated storm ID (e.g., 'al092026').
            template_path: Path to the bash script template.
            output_dir: Directory where the populated output file will be saved.
            
        Raises:
            ValueError: If the storm_id format is invalid.
            FileNotFoundError: If the template file does not exist.
        """
        if len(storm_id) != 8:
            raise ValueError(f"Invalid storm_id length: {len(storm_id)}. Expected 8 characters (e.g., 'al092026').")

        self.storm_id = storm_id
        self.template_path = template_path
        self.output_dir = output_dir or "."

        # 1. Parse storm_id
        # Format: [basin:2][number:2][year:4]
        self.storm = storm_id[2:4]
        self.year = storm_id[4:8]

        # 2. Read template and extract GRIDNAME
        grid_name = self._extract_grid_name()

        # 3. Fetch current system username
        username = getpass.getuser()

        # 4. Generate default replacement values (public attributes for user override)
        self._base_instance_name = f"{grid_name}_{self.storm_id}_{username}"
        self.instance_name = f"{grid_name}_{self.storm_id}_{username}"
        self.storm_scenerios = "" # Will be populated by TUI

    def _extract_grid_name(self) -> str:
        """
        Extracts the value associated with GRIDNAME from the template file.
        
        Returns:
            The extracted grid name string.
            
        Raises:
            FileNotFoundError: If the template file is not found.
            ValueError: If GRIDNAME is not found in the template.
        """
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(f"Template file not found: {self.template_path}")

        with open(self.template_path, 'r') as f:
            content = f.read()

        # Look for GRIDNAME=value or similar patterns
        # Using a regex to find GRIDNAME followed by an optional '=' and the value
        match = re.search(r"GRIDNAME\s*=\s*['\"]?([^'\"\s\n]+)['\"]?", content)
        if match:
            return match.group(1)
        
        # Fallback or specific error if GRIDNAME is mandatory
        raise ValueError(f"GRIDNAME not defined in template: {self.template_path}")

    def write_config(self) -> str:
        """
        Performs string replacements and writes the final config to output_dir.
        The filename is generated as {self.instance_name}.sh.
        
        Returns:
            The absolute path to the generated file.
        
        Replaces placeholders matching %ATTR% where ATTR is any attribute of this instance.
        """
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(f"Template file not found: {self.template_path}")

        with open(self.template_path, 'r') as f:
            content = f.read()

        # Perform replacements for all public attributes
        # This handles %YEAR%, %STORM%, %INSTANCENAME% and any new ones like %NCPU%
        for attr, value in self.__dict__.items():
            if not attr.startswith('_'):
                placeholder = f"%{attr.upper()}%"
                content = content.replace(placeholder, str(value))
        
        # Special case for instance_name as it's often referred to as %INSTANCENAME%
        content = content.replace("%INSTANCENAME%", str(self.instance_name))

        # Ensure output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        output_filename = f"{self.instance_name}.sh"
        output_path = os.path.join(self.output_dir, output_filename)

        with open(output_path, 'w') as f:
            f.write(content)
        
        return os.path.abspath(output_path)
