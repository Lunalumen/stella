---
name: java-exe-batch
description: Build and verify Windows console EXEs and runnable JARs from Java examples using an installed JDK and JSmooth. Use for individual or numbered classroom examples and repeatable batch packaging.
---

# Java 예제를 JAR과 EXE로 만들기

사용자가 지정한 소스와 출력 범위에서 작업한다. 교수의 PPT·성공한 설정이 있으면 먼저 확인한다. 다른 클래스·과제 전체로 범위를 확대하지 않는다.

## 준비

- 실제 JDK의 java.exe, javac.exe, jar.exe와 JSmooth의 jsmoothcmd.exe를 확인한다. Java 버전·플랫폼은 과제와 기존 Eclipse에 맞춘다. 설치·보안 설정 변경은 이 스킬이 자동 허용하지 않는다.
- 진입점은 파일명이 아니라 package와 main 메서드로 확인한다. 보조 클래스, 외부 라이브러리, 입력, 데이터 파일, GUI·파일쓰기·네트워크 동작을 먼저 살핀다.
- 원본은 유지하고 빌드 작업 폴더를 사용한다. 수정이 필요하면 원본 백업 후 승인된 최소 범위만 수정한다. 번호 예제끼리 보조 클래스 이름이 겹칠 수 있으므로 독립된 classes 폴더로 컴파일한다.
- Eclipse의 Package required libraries 방식은 JarRsrcLoader를 사용한다. main 클래스가 package-private이면 IllegalAccessException이 날 수 있다. public 선언이 필요한지 확인하되 일괄 치환하지 않는다. 코드를 바꿨으면 JAR·EXE를 다시 생성한다.

## 자동 생성

단순한 콘솔 예제는 [scripts/build-java-exes.ps1](scripts/build-java-exes.ps1)을 사용한다. 외부 라이브러리·공유 소스가 필요한 프로젝트는 해당 프로젝트의 빌드 도구로 JAR을 만들고 JSmooth에 연결한다. 제공 스크립트는 단일 소스로 컴파일되는 예제용이다.

```powershell
./scripts/build-java-exes.ps1 -SourceDirectory 'C:\project\src\demo' -Names @('Example2','Example3') -PackageName demo -JdkHome 'C:\Java\jdk8' -JsmoothHome 'C:\Tools\JSmooth' -OutputDirectory 'C:\results' -BuildDirectory 'C:\scratch\java-build' -VerifyConsole
```

- 기본 출력은 이름별 .jar, .exe, .jsmooth이다. 기존 출력이 있으면 스크립트가 중단한다. 별도 출력 폴더에서 검증한 뒤 기존 파일은 백업하고 전달한다.
- JAR에는 해당 소스로 컴파일된 보조·내부 클래스도 포함하고 Main-Class를 정확히 지정한다. 이 스크립트는 표준 manifest로 실행되는 독립 JAR을 생성하므로 Eclipse의 jar-in-jar 방식과 포장 방식은 다르다.
- EXE에는 Console Wrapper, embeddedJar, 정확한 main 클래스, 최소 JVM 버전과 PressKey를 지정한다. JRE 자체를 포함하는 것은 아니므로 실행 컴퓨터에 호환 Java가 필요하다.
- JSmooth의 JVM 탐색은 32/64비트 레지스트리에 따라 달라질 수 있다. JAVA_HOME과 PATH까지 확인하고 실제 EXE로 검증한다. JAR 성공만으로 EXE 성공을 보고하지 않는다.

## 검증·전달

소스를 검토해 부작용과 입력이 없는 콘솔 프로그램임을 확인한 경우에만 -VerifyConsole을 사용한다. JAR·EXE를 각각 제한 시간 내 실행하고 오류·종료 코드·출력을 비교한다. 입력·GUI·외부 파일 프로그램에는 자동 Enter 테스트를 적용하지 않고 명시한 테스트 절차를 사용한다.

PressKey의 대기 문구는 앱 출력과 구분한다. Windows Java 8 콘솔 출력은 CP949일 수 있다. 빌드 소스 인코딩, JAR 출력 UTF-8, EXE 출력 인코딩을 각각 다룬다. 검증 보고서는 로컬에 두고 개인 코드·경로·수업 자료·실행 결과를 스킬 저장소에 올리지 않는다.

전달 후 파일 개수와 복사 해시를 확인한다. 실제 실행한 범위와 미검증 사항을 간결히 보고한다. GUI로만 작업할 경우 사용 가능한 컴퓨터 사용 도구의 현재 창·확인 규칙을 따른다.
