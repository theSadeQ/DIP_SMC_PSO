@ECHO OFF

set SPHINXBUILD=sphinx-build
set SOURCEDIR=docs\source
set BUILDDIR=docs\build

if "%1" == "" goto help

%SPHINXBUILD% -M %1 %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%
goto end

:help
%SPHINXBUILD% -M help %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%

:end
