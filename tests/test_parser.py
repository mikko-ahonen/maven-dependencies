from maven_dependencies.pom_parser import parse_pom

POM = """<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.acme</groupId><artifactId>a</artifactId><version>1</version>
  <build>
    <plugins><plugin><groupId>org.apache.maven.plugins</groupId><artifactId>maven-compiler-plugin</artifactId><version>3.11.0</version></plugin></plugins>
    <extensions><extension><groupId>x</groupId><artifactId>ext</artifactId><version>1</version></extension></extensions>
  </build>
</project>"""

def test_parser_plugins_and_extensions():
    raw = parse_pom(POM, "x")
    assert raw.plugins[0].artifact_id == "maven-compiler-plugin"
    assert raw.extensions[0].artifact_id == "ext"
