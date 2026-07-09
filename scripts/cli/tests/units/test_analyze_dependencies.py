#!/usr/bin/env python3
"""Tests for analyze_dependencies.py"""

import pytest
from pathlib import Path

# Add parent directory to path for imports

from cli.analyze_dependencies import (
    analyze_package_json,
    analyze_requirements_txt,
    analyze_cargo_toml,
    analyze_go_mod,
    analyze_pom_xml,
    analyze_dependencies,
)

class TestAnalyzePackageJson:
    """Test Node.js package.json analysis."""

    def test_basic_dependencies(self):
        """Test extraction of basic dependencies."""
        content = """{
            "dependencies": {
                "express": "^4.18.0",
                "lodash": "^4.17.21"
            }
        }"""

        result = analyze_package_json(content, 10)

        assert result["language"] == "javascript"
        assert result["packageManager"] == "npm"
        assert len(result["dependencies"]) == 2
        assert result["dependencies"][0]["name"] == "express"
        assert result["dependencies"][0]["version"] == "^4.18.0"

    def test_dev_dependencies(self):
        """Test extraction of dev dependencies."""
        content = """{
            "dependencies": {
                "express": "^4.18.0"
            },
            "devDependencies": {
                "jest": "^29.0.0",
                "eslint": "^8.0.0"
            }
        }"""

        result = analyze_package_json(content, 10)

        assert len(result["devDependencies"]) == 2
        assert result["devDependencies"][0]["name"] == "jest"

    def test_framework_detection_react(self):
        """Test React framework detection."""
        content = """{
            "dependencies": {
                "react": "^18.0.0",
                "react-dom": "^18.0.0"
            }
        }"""

        result = analyze_package_json(content, 10)

        assert result["framework"] == "react"

    def test_framework_detection_vue(self):
        """Test Vue framework detection."""
        content = """{
            "dependencies": {
                "vue": "^3.0.0"
            }
        }"""

        result = analyze_package_json(content, 10)

        assert result["framework"] == "vue"

    def test_framework_detection_express(self):
        """Test Express framework detection."""
        content = """{
            "dependencies": {
                "express": "^4.18.0"
            }
        }"""

        result = analyze_package_json(content, 10)

        assert result["framework"] == "express"

    def test_scripts_extraction(self):
        """Test extraction of npm scripts."""
        content = """{
            "scripts": {
                "start": "node server.js",
                "test": "jest",
                "build": "webpack"
            }
        }"""

        result = analyze_package_json(content, 10)

        assert len(result["scripts"]) == 3
        assert result["scripts"]["start"] == "node server.js"
        assert result["scripts"]["test"] == "jest"

    def test_top_n_limit(self):
        """Test limiting number of dependencies returned."""
        content = """{
            "dependencies": {
                "dep1": "1.0.0",
                "dep2": "2.0.0",
                "dep3": "3.0.0",
                "dep4": "4.0.0",
                "dep5": "5.0.0"
            }
        }"""

        result = analyze_package_json(content, 3)

        assert len(result["dependencies"]) == 3

class TestAnalyzeRequirementsTxt:
    """Test Python requirements.txt analysis."""

    def test_basic_requirements(self):
        """Test extraction of basic requirements."""
        content = """django==4.2.0
flask>=2.0.0
requests"""

        result = analyze_requirements_txt(content, 10)

        assert result["language"] == "python"
        assert result["packageManager"] == "pip"
        assert len(result["dependencies"]) == 3
        assert result["dependencies"][0]["name"] == "django"
        assert result["dependencies"][0]["version"] == "==4.2.0"

    def test_comments_ignored(self):
        """Test that comments are ignored."""
        content = """# This is a comment
django==4.2.0
# Another comment
flask>=2.0.0"""

        result = analyze_requirements_txt(content, 10)

        assert len(result["dependencies"]) == 2

    def test_framework_detection_django(self):
        """Test Django framework detection."""
        content = """django==4.2.0
psycopg2==2.9.0"""

        result = analyze_requirements_txt(content, 10)

        assert result["framework"] == "django"

    def test_framework_detection_flask(self):
        """Test Flask framework detection."""
        content = """flask==2.3.0
werkzeug==2.3.0"""

        result = analyze_requirements_txt(content, 10)

        assert result["framework"] == "flask"

    def test_framework_detection_fastapi(self):
        """Test FastAPI framework detection."""
        content = """fastapi==0.100.0
uvicorn==0.23.0"""

        result = analyze_requirements_txt(content, 10)

        assert result["framework"] == "fastapi"

    def test_version_operators(self):
        """Test different version operators."""
        content = """package1==1.0.0
package2>=2.0.0
package3~=3.0.0
package4"""

        result = analyze_requirements_txt(content, 10)

        assert result["dependencies"][0]["version"] == "==1.0.0"
        assert result["dependencies"][1]["version"] == ">=2.0.0"
        assert result["dependencies"][2]["version"] == "~=3.0.0"
        assert result["dependencies"][3]["version"] == "any"

class TestAnalyzeCargoToml:
    """Test Rust Cargo.toml analysis."""

    def test_basic_dependencies(self):
        """Test extraction of basic dependencies."""
        content = """[package]
name = "myproject"

[dependencies]
serde = "1.0"
tokio = "1.28"
"""

        result = analyze_cargo_toml(content, 10)

        assert result["language"] == "rust"
        assert result["packageManager"] == "cargo"
        assert len(result["dependencies"]) == 2
        assert result["dependencies"][0]["name"] == "serde"
        assert result["dependencies"][0]["version"] == "1.0"

    def test_dependencies_with_features(self):
        """Test dependencies with features."""
        content = """[dependencies]
tokio = { version = "1.28", features = ["full"] }
serde = "1.0"
"""

        result = analyze_cargo_toml(content, 10)

        assert len(result["dependencies"]) == 2
        assert result["dependencies"][0]["name"] == "tokio"
        assert result["dependencies"][0]["version"] == "1.28"

    def test_framework_detection_actix(self):
        """Test Actix Web framework detection."""
        content = """[dependencies]
actix-web = "4.0"
actix-rt = "2.0"
"""

        result = analyze_cargo_toml(content, 10)

        assert result["framework"] == "actix-web"

    def test_framework_detection_rocket(self):
        """Test Rocket framework detection."""
        content = """[dependencies]
rocket = "0.5"
"""

        result = analyze_cargo_toml(content, 10)

        assert result["framework"] == "rocket"

class TestAnalyzeGoMod:
    """Test Go go.mod analysis."""

    def test_basic_dependencies(self):
        """Test extraction of basic dependencies."""
        content = """module github.com/myorg/myproject

go 1.20

require (
	github.com/gin-gonic/gin v1.9.0
	github.com/stretchr/testify v1.8.0
)
"""

        result = analyze_go_mod(content, 10)

        assert result["language"] == "go"
        assert result["packageManager"] == "go"
        assert len(result["dependencies"]) == 2
        assert result["dependencies"][0]["name"] == "github.com/gin-gonic/gin"
        assert result["dependencies"][0]["version"] == "v1.9.0"

    def test_framework_detection_gin(self):
        """Test Gin framework detection."""
        content = """require (
	github.com/gin-gonic/gin v1.9.0
)
"""

        result = analyze_go_mod(content, 10)

        assert result["framework"] == "gin"

    def test_framework_detection_echo(self):
        """Test Echo framework detection."""
        content = """require (
	github.com/labstack/echo/v4 v4.11.0
)
"""

        result = analyze_go_mod(content, 10)

        assert result["framework"] == "echo"

    def test_framework_detection_fiber(self):
        """Test Fiber framework detection."""
        content = """require (
	github.com/gofiber/fiber/v2 v2.48.0
)
"""

        result = analyze_go_mod(content, 10)

        assert result["framework"] == "fiber"

class TestAnalyzePomXml:
    """Test Java/Maven pom.xml analysis."""

    def test_basic_dependencies(self):
        """Test extraction of basic dependencies."""
        content = """<?xml version="1.0"?>
<project>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-web</artifactId>
      <version>3.0.0</version>
    </dependency>
    <dependency>
      <groupId>junit</groupId>
      <artifactId>junit</artifactId>
      <version>4.13.2</version>
    </dependency>
  </dependencies>
</project>
"""

        result = analyze_pom_xml(content, 10)

        assert result["language"] == "java"
        assert result["packageManager"] == "maven"
        assert len(result["dependencies"]) == 2
        assert result["dependencies"][0]["name"] == "org.springframework.boot:spring-boot-starter-web"
        assert result["dependencies"][0]["version"] == "3.0.0"

    def test_framework_detection_spring(self):
        """Test Spring framework detection."""
        content = """<?xml version="1.0"?>
<project>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter</artifactId>
      <version>3.0.0</version>
    </dependency>
  </dependencies>
</project>
"""

        result = analyze_pom_xml(content, 10)

        assert result["framework"] == "spring"

class TestAnalyzeDependencies:
    """Test main analyze_dependencies function."""

    def test_file_not_found(self):
        """Test error when file not found."""
        with pytest.raises(FileNotFoundError):
            analyze_dependencies(Path("/nonexistent/file.json"))

    def test_unsupported_file_type(self, tmp_path):
        """Test error for unsupported file type."""
        test_file = tmp_path / "unknown.txt"
        test_file.write_text("content")

        with pytest.raises(ValueError, match="Unsupported package file"):
            analyze_dependencies(test_file)

    def test_package_json_analysis(self, tmp_path):
        """Test analysis of package.json file."""
        package_json = tmp_path / "package.json"
        package_json.write_text("""{
            "dependencies": {
                "react": "^18.0.0"
            }
        }""")

        result = analyze_dependencies(package_json)

        assert result["language"] == "javascript"
        assert result["framework"] == "react"
        assert result["file"] == str(package_json)

    def test_requirements_txt_analysis(self, tmp_path):
        """Test analysis of requirements.txt file."""
        requirements = tmp_path / "requirements.txt"
        requirements.write_text("django==4.2.0\nflask>=2.0.0")

        result = analyze_dependencies(requirements)

        assert result["language"] == "python"
        assert result["framework"] == "django"

    def test_cargo_toml_analysis(self, tmp_path):
        """Test analysis of Cargo.toml file."""
        cargo_toml = tmp_path / "Cargo.toml"
        cargo_toml.write_text("""[dependencies]
serde = "1.0"
""")

        result = analyze_dependencies(cargo_toml)

        assert result["language"] == "rust"

    def test_go_mod_analysis(self, tmp_path):
        """Test analysis of go.mod file."""
        go_mod = tmp_path / "go.mod"
        go_mod.write_text("""require (
	github.com/gin-gonic/gin v1.9.0
)
""")

        result = analyze_dependencies(go_mod)

        assert result["language"] == "go"
        assert result["framework"] == "gin"

    def test_pom_xml_analysis(self, tmp_path):
        """Test analysis of pom.xml file."""
        pom_xml = tmp_path / "pom.xml"
        pom_xml.write_text("""<?xml version="1.0"?>
<project>
  <dependencies>
    <dependency>
      <groupId>junit</groupId>
      <artifactId>junit</artifactId>
      <version>4.13.2</version>
    </dependency>
  </dependencies>
</project>
""")

        result = analyze_dependencies(pom_xml)

        assert result["language"] == "java"

    def test_top_n_parameter(self, tmp_path):
        """Test top_n parameter limits results."""
        package_json = tmp_path / "package.json"
        package_json.write_text("""{
            "dependencies": {
                "dep1": "1.0.0",
                "dep2": "2.0.0",
                "dep3": "3.0.0",
                "dep4": "4.0.0",
                "dep5": "5.0.0"
            }
        }""")

        result = analyze_dependencies(package_json, top_n=3)

        assert len(result["dependencies"]) == 3
