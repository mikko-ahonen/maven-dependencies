from maven_dependencies.pom_parser import parse_pom
from maven_dependencies.effective import make_effective_pom

PARENT = """<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.acme</groupId>
  <artifactId>parent</artifactId>
  <version>1.0.0</version>
  <properties><dep.version>2.0.0</dep.version></properties>
  <dependencyManagement><dependencies>
    <dependency><groupId>x</groupId><artifactId>y</artifactId><version>${dep.version}</version></dependency>
  </dependencies></dependencyManagement>
</project>"""

CHILD = """<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <parent><groupId>com.acme</groupId><artifactId>parent</artifactId><version>1.0.0</version></parent>
  <artifactId>child</artifactId>
  <dependencies>
    <dependency><groupId>x</groupId><artifactId>y</artifactId></dependency>
  </dependencies>
</project>"""

def test_parent_inheritance_and_dm():
    parent = make_effective_pom(parse_pom(PARENT, "parent"), None, "none", None)
    child = make_effective_pom(parse_pom(CHILD, "child"), parent, "none", None)
    dep = child.dependencies[0]
    assert child.coordinate.gav == "com.acme:child:1.0.0"
    assert dep.version == "2.0.0"
