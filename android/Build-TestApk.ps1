param(
    [string]$SdkRoot = $env:ANDROID_HOME,
    [string]$JdkDir = $env:JAVA_HOME,
    [string]$PlatformJar,
    [string]$BuildToolsDir,
    [string]$OutputApk = (Join-Path $PSScriptRoot 'build/local/matchindex-overlay-test.apk')
)

$ErrorActionPreference = 'Stop'
$MinimumSdk = 26
$TargetSdk = 36
if (!$PlatformJar -or !$BuildToolsDir) {
    if (!$SdkRoot) { throw 'Set ANDROID_HOME or pass -PlatformJar and -BuildToolsDir.' }
}
if (!$PlatformJar) { $PlatformJar = Join-Path $SdkRoot 'platforms/android-36/android.jar' }
if (!$BuildToolsDir) { $BuildToolsDir = Join-Path $SdkRoot 'build-tools/36.0.0' }
$buildDir = $BuildToolsDir
if (!$JdkDir -or !(Test-Path -LiteralPath (Join-Path $JdkDir 'bin/javac.exe')) -or
    !(Test-Path -LiteralPath $PlatformJar) -or !(Test-Path -LiteralPath (Join-Path $buildDir 'aapt2.exe'))) {
    throw 'Install a JDK, Android SDK Platform 36, and Android Build Tools 36.0.0.'
}
$toolsRoot = Join-Path $PSScriptRoot 'build'
New-Item -ItemType Directory -Path $toolsRoot -Force | Out-Null
$sourceRoot = Join-Path $PSScriptRoot 'app/src/main'
$manifest = Join-Path $sourceRoot 'AndroidManifest.xml'
$resources = Join-Path $sourceRoot 'res'
$assets = Join-Path $sourceRoot 'assets'
$jobRoot = Join-Path $toolsRoot ('build-' + [guid]::NewGuid().ToString('N'))
$classes = Join-Path $jobRoot 'classes'
$javaSources = Join-Path $jobRoot 'generated'
$dexDir = Join-Path $jobRoot 'dex'
New-Item -ItemType Directory -Path $jobRoot,$classes,$javaSources,$dexDir | Out-Null

[xml]$manifestXml = Get-Content -Raw -LiteralPath $manifest
if (!$manifestXml.DocumentElement.GetAttribute('package')) {
    $javaFile = Get-ChildItem (Join-Path $sourceRoot 'java') -Recurse -Filter '*.java' | Select-Object -First 1
    if (!$javaFile) { throw 'No Java entry to determine manifest package' }
    $declaredPackage = [regex]::Match([IO.File]::ReadAllText($javaFile.FullName),'(?m)^package\s+([\w.]+)\s*;').Groups[1].Value
    if (!$declaredPackage) { throw 'Java entry does not declare a package' }
    $manifestXml.DocumentElement.SetAttribute('package',$declaredPackage)
    $manifest = Join-Path $jobRoot 'AndroidManifest.xml'
    $manifestXml.Save($manifest)
}

function Run-Tool([string]$Path) {
    & $Path @args
    if ($LASTEXITCODE -ne 0) { throw "Android tool failed: $Path exit $LASTEXITCODE" }
}

$aapt = Join-Path $buildDir 'aapt2.exe'
$unsigned = Join-Path $jobRoot 'unsigned.apk'
$javaHomeBefore = $env:JAVA_HOME
$pathBefore = $env:Path
try {
    $env:JAVA_HOME = $jdkDir
    $env:Path = (Join-Path $jdkDir 'bin') + ';' + $pathBefore
    $link = @('link','-I',$platformJar,'--manifest',$manifest,'--min-sdk-version',"$MinimumSdk",'--target-sdk-version',"$TargetSdk",'--version-code','5','--version-name','0.1.4-test','--java',$javaSources,'-o',$unsigned)
    if (Test-Path -LiteralPath $resources -PathType Container) {
        $resourceZip = Join-Path $jobRoot 'resources.zip'
        Run-Tool $aapt 'compile' '--dir' $resources '-o' $resourceZip
        $link += @('--auto-add-overlay','-R',$resourceZip)
    }
    if (Test-Path -LiteralPath $assets -PathType Container) { $link += @('-A',$assets) }
    Run-Tool $aapt @link
    $inputs = @(Get-ChildItem (Join-Path $sourceRoot 'java'),$javaSources -Recurse -Filter '*.java' | Select-Object -ExpandProperty FullName)
    if (!$inputs.Count) { throw 'No Java source files found' }
    Run-Tool (Join-Path $jdkDir 'bin/javac.exe') '-encoding' 'UTF-8' '-source' '8' '-target' '8' '-Xlint:-options' '-bootclasspath' ((Join-Path $buildDir 'core-lambda-stubs.jar') + ';' + $platformJar) '-d' $classes @inputs
    $compiledJar = Join-Path $jobRoot 'compiled.jar'
    Run-Tool (Join-Path $jdkDir 'bin/jar.exe') '--create' '--file' $compiledJar '-C' $classes '.'
    Run-Tool (Join-Path $buildDir 'd8.bat') '--lib' $platformJar '--output' $dexDir '--min-api' "$MinimumSdk" $compiledJar
    $dexFiles = @(Get-ChildItem -LiteralPath $dexDir -Filter '*.dex')
    if (!$dexFiles.Count) { throw 'D8 did not produce a DEX file' }
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $apkArchive = [IO.Compression.ZipFile]::Open($unsigned,[IO.Compression.ZipArchiveMode]::Update)
    try {
        foreach ($dex in $dexFiles) {
            [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($apkArchive,$dex.FullName,$dex.Name) | Out-Null
        }
    } finally {
        $apkArchive.Dispose()
    }
    $aligned = Join-Path $jobRoot 'aligned.apk'
    Run-Tool (Join-Path $buildDir 'zipalign.exe') '-f' '-p' '4' $unsigned $aligned
    $debugKey = Join-Path $toolsRoot 'matchindex-test-signing.p12'
    $debugAlias = 'matchindex-test'
    if (!(Test-Path -LiteralPath $debugKey)) {
        Run-Tool (Join-Path $jdkDir 'bin/keytool.exe') '-genkeypair' '-keystore' $debugKey '-storetype' 'PKCS12' '-storepass' 'android' '-keypass' 'android' '-alias' $debugAlias '-keyalg' 'RSA' '-keysize' '2048' '-validity' '3650' '-dname' 'CN=MatchIndex Test Signing'
    }
    $destination = [IO.Path]::GetFullPath($OutputApk)
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    Run-Tool (Join-Path $buildDir 'apksigner.bat') 'sign' '--ks' $debugKey '--ks-key-alias' $debugAlias '--ks-pass' 'pass:android' '--key-pass' 'pass:android' '--out' $destination $aligned
    Run-Tool (Join-Path $buildDir 'zipalign.exe') '-c' '-p' '4' $destination
    Run-Tool (Join-Path $buildDir 'apksigner.bat') 'verify' '--verbose' $destination
    Run-Tool $aapt 'dump' 'badging' $destination
    Get-FileHash -Algorithm SHA256 -LiteralPath $destination
} finally {
    $env:JAVA_HOME = $javaHomeBefore
    $env:Path = $pathBefore
}
