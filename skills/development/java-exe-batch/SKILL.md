---
name: java-exe-batch
description: Build and verify Windows console EXEs and runnable JARs from classroom Java examples. Preserve a user-confirmed C# console launcher or use JSmooth when required; support single-example checks before batch packaging.
---

# Java 예제를 JAR과 EXE로 만들기

## 최우선 1번 — 실제 성공한 콘솔형 EXE 제작법 보존

2026-11-05 사용자가 Ex9_4 단일 EXE를 직접 실행하고 “실제로 된다, 실행 눌러도 가능”이라고 확인했다. **이 사용자의 Java EXE 복구 작업에서는 아래 방법을 가장 먼저 참고한다.** 사용자가 요구한 것은 기존처럼 검은 콘솔 창에 결과를 출력하는 EXE이며, 별도 결과창·버튼 방식은 제출용으로 거절했다. 성공본을 임의로 JSmooth 또는 GUI 실행기로 되돌리지 않는다. 교수 자료를 정확히 따르라는 별도 요구가 있으면 그 요구와 복구 방식을 구분한다.

- **성공 기술:** runnable JAR을 C# EXE의 `application.jar` 리소스로 내장한다. Windows .NET Framework `csc.exe`에 `/target:exe /platform:anycpu /optimize+`를 지정해 **콘솔형** 실행기로 빌드한다. `/target:winexe`를 쓰지 않는다.
- 실행 시 고유 임시 폴더에 JAR을 추출하고 `JAVA_HOME` → Java 레지스트리 → PATH에서 Java를 찾는다. Java를 직접 실행하면서 `-Dfile.encoding=UTF-8`, `UseShellExecute=false`, `CreateNoWindow=true` 및 표준 출력·오류 리디렉션을 사용한다. 읽기는 비동기로 처리한다.
- 수집한 결과와 오류를 EXE 자신의 콘솔에 출력한다. 끝에서 `Console.ReadKey(true)`로 사용자가 키를 누를 때까지 기다린다. 입력이 리디렉션된 자동 검사에서는 대기하지 않는다. Java 소스의 계산 로직은 바꾸지 않는다.
- 재현용 파일은 [assets/ConsoleLauncher.cs](assets/ConsoleLauncher.cs)와 [scripts/build-java-console-exe.ps1](scripts/build-java-console-exe.ps1)이다. `-JarPath`, `-OutputPath`, `-BuildDirectory`, 필요 시 `-DefaultArguments`를 지정한다. PowerShell 7에서 실행한다. 실행 PC에는 호환 Java와 .NET Framework 4.5 이상이 필요하다. Java 자체를 EXE에 포함한 방식은 아니다.
- 검토한 입력 없는 예제에만 `-ExpectedOutputFile`을 주어 내부 실행 경로의 출력을 비교한다. 정상 콘솔 창 확인·ZIP 직접 실행·사이트 재다운로드·다른 PC 실행은 각각 따로 기록한다. 사용자가 확인한 사실은 해당 Ex9_4의 실제 실행 성공이며, 다른 PC나 모든 ZIP에 대한 보장은 아니다.
- **한 개부터:** 사용자가 Ex9_4 하나만 요청했으면 하나만 만든다. 그 파일의 실제 실행 확인 후 나머지는 사용자가 요청할 때 진행한다. 단일 성공만으로 일괄 생성 개수가 기존 실패 원인이었다고 단정하지 않는다.

사용자가 지정한 소스와 출력 범위에서 작업한다. 교수의 PPT·성공한 설정이 있으면 먼저 확인한다. 다른 클래스·과제 전체로 범위를 확대하지 않는다.

## 준비

- 실제 JDK의 java.exe, javac.exe, jar.exe와 JSmooth의 jsmoothcmd.exe를 확인한다. Java 버전·플랫폼은 과제와 기존 Eclipse에 맞춘다. 설치·보안 설정 변경은 이 스킬이 자동 허용하지 않는다.
- 진입점은 파일명이 아니라 package와 main 메서드로 확인한다. 보조 클래스, 외부 라이브러리, 입력, 데이터 파일, GUI·파일쓰기·네트워크 동작을 먼저 살핀다.
- 원본은 유지하고 빌드 작업 폴더를 사용한다. 수정이 필요하면 원본 백업 후 승인된 최소 범위만 수정한다. 번호 예제끼리 보조 클래스 이름이 겹칠 수 있으므로 독립된 classes 폴더로 컴파일한다.
- 정상 실행되는 이전 ZIP을 제공받으면 그 안의 EXE 해시와 보관한 제작본을 대조한다. JVM 탐색 순서·main 클래스·JAR manifest·PressKey를 비교하고, 사용자가 이전 방식으로 복원을 요청하면 그 설정을 기준으로 삼는다. 다른 예제의 해시가 서로 다른 것은 정상이다.
- Eclipse의 Package required libraries 방식은 JarRsrcLoader를 사용한다. main 클래스가 package-private이면 IllegalAccessException이 날 수 있다. public 선언이 필요한지 확인하되 일괄 치환하지 않는다. 코드를 바꿨으면 JAR·EXE를 다시 생성한다.

## 자동 생성

JSmooth가 필요한 작업은 [scripts/build-java-exes.ps1](scripts/build-java-exes.ps1)을 사용한다. 이 사용자의 실행 복구는 위의 최우선 콘솔형 실행기를 먼저 참고한다. 외부 라이브러리·공유 소스가 필요한 프로젝트는 해당 프로젝트의 빌드 도구로 JAR을 만든다. 기존 JSmooth 스크립트는 단일 소스로 컴파일되는 예제용이다.

스크립트는 PowerShell 7에서 실행한다. 클래스별 기본 인수는 `-DefaultArguments @{Example3=@('10','20','30')}`로 지정한다. 현재 인수 입력은 공백·따옴표·역슬래시가 없는 단순 토큰만 지원한다. 값을 임의로 정하지 말고 기존 실행 설정이나 사용자 지정값을 사용한다.

```powershell
./scripts/build-java-exes.ps1 -SourceDirectory 'C:\project\src\demo' -Names @('Example2','Example3') -PackageName demo -JdkHome 'C:\Java\jdk8' -JsmoothHome 'C:\Tools\JSmooth' -OutputDirectory 'C:\results' -BuildDirectory 'C:\scratch\java-build' -VerifyConsole
```

- 기본 출력은 이름별 .jar, .exe, .jsmooth이다. 기존 출력이 있으면 스크립트가 중단한다. 별도 출력 폴더에서 검증한 뒤 기존 파일은 백업하고 전달한다.
- JAR에는 해당 소스로 컴파일된 보조·내부 클래스도 포함하고 Main-Class를 정확히 지정한다. 이 스크립트는 표준 manifest로 실행되는 독립 JAR을 생성하므로 Eclipse의 jar-in-jar 방식과 포장 방식은 다르다.
- EXE에는 Console Wrapper, embeddedJar, 정확한 main 클래스, 최소 JVM 버전과 PressKey를 지정한다. JRE 자체를 포함하는 것은 아니므로 실행 컴퓨터에 호환 Java가 필요하다.
- JSmooth의 JVM 탐색은 32/64비트 레지스트리에 따라 달라질 수 있다. JAVA_HOME과 PATH까지 확인하고 실제 EXE로 검증한다. JAR 성공만으로 EXE 성공을 보고하지 않는다.
- 기본 스크립트는 JAVA_HOME → registry → PATH 순서, main 직접 실행, PressKey를 사용한다. PPT 설정을 정확히 따르는 작업과 이전 성공본을 복원하는 작업을 구분한다.
- JSmooth가 일부 내장 JAR 크기에서 PE 섹션 주소를 잘못 정렬한 사례가 있었다. 스크립트는 생성된 EXE의 섹션 주소 정렬을 검사하고, 실패하면 같은 클래스들을 무압축 JAR로 다시 포장해 한 번 재생성한다. 재검사도 실패하면 중단한다. 이는 모든 EXE 미실행 증상의 원인이 아니며, 바이너리 주소를 임의로 고치지 않는다. 규칙은 [Microsoft PE 형식](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format)의 Section Table을 참고한다.

## 검증·전달

소스를 검토해 부작용과 입력이 없는 콘솔 프로그램임을 확인한 경우에만 -VerifyConsole을 사용한다. JAR·EXE를 각각 제한 시간 내 실행하고 오류·종료 코드·출력을 비교한다. 입력·GUI·외부 파일 프로그램에는 자동 Enter 테스트를 적용하지 않고 명시한 테스트 절차를 사용한다.

PressKey의 대기 문구는 앱 출력과 구분한다. Windows Java 8 콘솔 출력은 CP949일 수 있다. 빌드 소스 인코딩, JAR 출력 UTF-8, EXE 출력 인코딩을 각각 다룬다. 검증 보고서는 로컬에 두고 개인 코드·경로·수업 자료·실행 결과를 스킬 저장소에 올리지 않는다.

- `-ZipPath 'C:\results\examples.zip'`은 지정한 EXE만 압축한다. ZIP 해제본의 해시를 확인하고, `-VerifyConsole`과 함께 쓰면 해제본도 다시 실행한다. 기존 ZIP·출력 파일은 덮어쓰지 않는다.
- `ConsoleVerified`는 창 없이 출력을 수집한 검사다. 실제 결과창 표시, ZIP 탐색기에서 직접 실행, 사이트 업로드·재다운로드, 다른 PC 실행은 각각 별도 검증이다. 로컬 ZIP 해제본 검사만으로 이 항목들까지 성공했다고 보고하지 않는다.
- 출력을 못 얻었으면 재압축을 반복하지 말고 정상 EXE와 같은 조건에서 비교한다. 필요하면 공식 [JSmooth 진단 옵션](https://jsmooth.sourceforge.net/docs/jsmooth-doc.html) `-JskelDebug=1`로 JVM 탐색 로그를 수집한다. 필요한 프로그램 인수도 함께 전달한다.
- 이벤트 1000의 DLL 이름만으로 원인을 확정하지 않는다. 파일 해시가 같아도 실행 환경까지 같은 것은 아니다. 테스트 실행의 TEMP/TMP가 실제 사용자 환경과 다른지 확인하되 보안 표식을 지우거나 보호 설정을 바꿔 통과시키지 않는다.

전달 후 파일 개수와 복사 해시를 확인한다. 실제 실행한 범위와 미검증 사항을 간결히 보고한다. GUI로만 작업할 경우 사용 가능한 컴퓨터 사용 도구의 현재 창·확인 규칙을 따른다.
