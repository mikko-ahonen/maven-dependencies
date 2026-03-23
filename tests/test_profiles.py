from maven_dependencies.pom_parser import parse_pom
from maven_dependencies.effective import make_effective_pom

POM = """<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.acme</groupId><artifactId>a</artifactId><version>1</version>
  <profiles>
    <profile>
      <id>prod</id>
      <dependencies>
        <dependency><groupId>x</groupId><artifactId>y</artifactId><version>1</version></dependency>
      </dependencies>
    </profile>
  </profiles>
</project>"""

def test_all_profiles_mode_includes_profile_dependency():
    eff = make_effective_pom(parse_pom(POM, "x"), None, "all", None)
    assert len(eff.dependencies) == 1
