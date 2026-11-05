using System;
using System.Collections.Generic;
using System.Diagnostics;

using System.IO;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;

using Microsoft.Win32;

internal sealed class RunResult
{
    public int Code;
    public string Output;
    public string Error;
}

internal static class JavaRunner
{
    private static IEnumerable<string> Candidates()
    {
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var paths = new List<string>();
        foreach (string variable in new[] { "JAVA_HOME", "JDK_HOME", "JRE_HOME" })
        {
            string home = Environment.GetEnvironmentVariable(variable);
            if (!String.IsNullOrWhiteSpace(home)) paths.Add(Path.Combine(home.Trim('"'), "bin", "java.exe"));
        }
        foreach (RegistryView view in new[] { RegistryView.Registry64, RegistryView.Registry32 })
        {
            try
            {
                using (RegistryKey root = RegistryKey.OpenBaseKey(RegistryHive.LocalMachine, view))
                foreach (string branch in new[] { @"SOFTWARE\JavaSoft\Java Runtime Environment", @"SOFTWARE\JavaSoft\JRE", @"SOFTWARE\JavaSoft\Java Development Kit", @"SOFTWARE\JavaSoft\JDK" })
                using (RegistryKey key = root.OpenSubKey(branch))
                {
                    if (key == null) continue;
                    var versions = new List<string>();
                    string current = key.GetValue("CurrentVersion") as string;
                    if (current != null) versions.Add(current);
                    versions.AddRange(key.GetSubKeyNames());
                    foreach (string version in versions)
                    using (RegistryKey entry = key.OpenSubKey(version))
                    {
                        string home = entry == null ? null : entry.GetValue("JavaHome") as string;
                        if (home != null) paths.Add(Path.Combine(home, "bin", "java.exe"));
                    }
                }
            }
            catch (System.Security.SecurityException) { }
            catch (UnauthorizedAccessException) { }
        }
        foreach (string directory in (Environment.GetEnvironmentVariable("PATH") ?? "").Split(';'))
        {
            try { if (!String.IsNullOrWhiteSpace(directory)) paths.Add(Path.Combine(directory.Trim('"'), "java.exe")); }
            catch (ArgumentException) { }
        }
        foreach (string path in paths) if (File.Exists(path) && seen.Add(path)) yield return path;
    }

    // Windows argument quoting, including trailing backslashes and embedded quotes.
    private static string Quote(string value)
    {
        var b = new StringBuilder("\"");
        int slashes = 0;
        foreach (char c in value)
        {
            if (c == '\\') { slashes++; continue; }
            if (c == '"') { b.Append('\\', slashes * 2 + 1); b.Append(c); }
            else { b.Append('\\', slashes); b.Append(c); }
            slashes = 0;
        }
        b.Append('\\', slashes * 2); b.Append('"');
        return b.ToString();
    }

    public static RunResult Run()
    {
        string folder = Path.Combine(Path.GetTempPath(), "JavaResult-" + Guid.NewGuid().ToString("N"));
        string jar = Path.Combine(folder, "application.jar");
        try
        {
            string java = null;
            foreach (string candidate in Candidates()) { java = candidate; break; }
            if (java == null) throw new InvalidOperationException("Java를 찾지 못했습니다. Java 8 이상을 설치하고 JAVA_HOME 또는 PATH를 확인해 주세요.");
            Directory.CreateDirectory(folder);
            using (Stream source = Assembly.GetExecutingAssembly().GetManifestResourceStream("application.jar"))
            using (FileStream target = new FileStream(jar, FileMode.CreateNew, FileAccess.Write))
            {
                if (source == null) throw new InvalidOperationException("프로그램이 EXE에 포함되지 않았습니다.");
                source.CopyTo(target);
            }
            var arguments = new StringBuilder("-Dfile.encoding=UTF-8 -jar " + Quote(jar));
            foreach (string arg in AppConfig.Arguments) arguments.Append(" " + Quote(arg));
            var info = new ProcessStartInfo(java, arguments.ToString());
            info.UseShellExecute = false;
            info.CreateNoWindow = true;
            info.WorkingDirectory = folder;
            info.RedirectStandardOutput = true;
            info.RedirectStandardError = true;
            info.RedirectStandardInput = true;
            info.StandardOutputEncoding = Encoding.UTF8;
            info.StandardErrorEncoding = Encoding.UTF8;
            using (Process process = Process.Start(info))
            {
                Task<string> output = process.StandardOutput.ReadToEndAsync();
                Task<string> error = process.StandardError.ReadToEndAsync();
                process.StandardInput.Close();
                if (!process.WaitForExit(15000))
                {
                    process.Kill(); process.WaitForExit();
                    throw new TimeoutException("15초 안에 실행이 끝나지 않았습니다. 이 실행기는 입력을 기다리지 않는 수업 예제용입니다.");
                }
                return new RunResult { Code = process.ExitCode, Output = output.Result, Error = error.Result };
            }
        }
        catch (Exception e) { return new RunResult { Code = -1, Output = "", Error = e.Message }; }
        finally
        {
            try { if (File.Exists(jar)) File.Delete(jar); if (Directory.Exists(folder)) Directory.Delete(folder); }
            catch (IOException) { }
            catch (UnauthorizedAccessException) { }
        }
    }
}

internal static class ConsoleEntry
{
    static int Main(string[] args)
    {
        RunResult result = JavaRunner.Run();
        if (args.Length == 2 && args[0] == "--verify-output")
        {
            using (var file = new FileStream(args[1], FileMode.CreateNew, FileAccess.Write))
            using (var writer = new StreamWriter(file, new UTF8Encoding(false)))
                writer.Write(result.Output + (String.IsNullOrEmpty(result.Error) ? "" : "\n[ERROR]\n" + result.Error));
            return result.Code;
        }
        Console.OutputEncoding = new UTF8Encoding(false);
        Console.Title = AppConfig.Name;
        Console.Write(result.Output);
        if (!String.IsNullOrWhiteSpace(result.Error)) Console.WriteLine("\n[실행 오류]\n" + result.Error);
        Console.WriteLine();
        Console.WriteLine("계속하려면 아무 키나 누르십시오 . . .");
        if (!Console.IsInputRedirected) Console.ReadKey(true);
        return result.Code;
    }
}

