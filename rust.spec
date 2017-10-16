# Fix to work around missing (not required) dependency
# libpthread.so.0(GLIBC_PRIVATE)
%global __requires_exclude libpthread.so.0
%define debug_package %{nil}
%define _disable_lto 1
%define _disable_ld_no_undefined 1
# To avoid undefined symbols
%define _find_debuginfo_opts -g

%bcond_with bootstrap
# (tpg) accordig to Rust devs a LLVM-5.0.0 is not yet supported
%bcond_with llvm
%define oname rustc

# Only x86_64 and i686 are Tier 1 platforms at this time.
# https://forge.rust-lang.org/platform-support.html
%global rust_arches x86_64 %ix86 armv7hl aarch64

Summary:	A safe, concurrent, practical programming language
Name:		rust
Version:	1.21.0
Release:	2
Group:		Development/Other
License:	MIT
Url:		http://www.rust-lang.org/
Source0:	http://static.rust-lang.org/dist/%{oname}-%{version}-src.tar.gz
Source100:	rust.rpmlintrc
BuildRequires:	python < 3.0
BuildRequires:	cmake
BuildRequires:	curl
BuildRequires:	procps-ng
BuildRequires:	flex
BuildRequires:	bison
BuildRequires:	gdb
BuildRequires:	git
%if %{with llvm}
BuildRequires:	llvm-devel
%endif
%if !%{with bootstrap}
BuildRequires:	rust
BuildRequires:	cargo
%endif
Provides:	%{oname} = %{EVRD}
# The C compiler is needed at runtime just for linking.  Someday rustc might
# invoke the linker directly, and then we'll only need binutils.
# https://github.com/rust-lang/rust/issues/11937
Requires:	gcc

# Get the Rust triple for any arch.
%{lua: function rust_triple(arch)
  local abi = "gnu"
  if arch == "armv7hl" then
    arch = "armv7"
    abi = "gnueabihf"
  elseif arch == "ppc64" then
    arch = "powerpc64"
  elseif arch == "ppc64le" then
    arch = "powerpc64le"
  elseif arch == "i586" then
    arch = "i686"
  end
  return arch.."-unknown-linux-"..abi
end}

%global rust_triple %{lua: print(rust_triple(rpm.expand("%{_target_cpu}")))}

%description
Rust is a curly-brace, block-structured expression language. It
visually resembles the C language family, but differs significantly
in syntactic and semantic details. Its design is oriented toward
concerns of "programming in the large", that is, of creating and
maintaining boundaries - both abstract and operational - that
preserve large-system integrity, availability and concurrency.

It supports a mixture of imperative procedural, concurrent actor,
object-oriented and pure functional styles. Rust also supports
generic programming and metaprogramming, in both static and dynamic
styles.

%package src
Summary:	Sources for the Rust standard library
BuildArch:	noarch

%description src
This package includes source files for the Rust standard library.
It may be useful as a reference for code completion tools in
various editors.

%prep
%setup -q -n %{oname}-%{version}-src

%if %{with llvm}
rm -rf src/llvm/
%endif

%build
%setup_compile_flags

# We're going to override --libdir when configuring to get rustlib into a
# common path, but we'll fix the shared libraries during install.
%global common_libdir %{_prefix}/lib
%global rustlibdir %{common_libdir}/rustlib

%if !%{with llvm}
export CC=gcc
export CXX=g++
# for some reason parts of the code still use cc call rather than the environment
# which results in a mixture
mkdir omv_build_comp
ln -s `which gcc` omv_build_comp/cc
ln -s `which g++` omv_build_comp/g++
export PATH=$PWD/omv_build_comp:$PATH
%endif

export RUST_BACKTRACE=1
export RUSTFLAGS="-Clink-arg=-Wl,-z,relro,-z,now"

# Unable to use standard configure as rust's configure is missing
# many of the options as commented out below from the configure2_5x macro
./configure \
	--prefix=%{_prefix} \
	--sysconfdir=%{_sysconfdir} \
	--datadir=%{_datadir} \
	--localstatedir=%{_localstatedir} \
	--mandir=%{_mandir} \
	--infodir=%{_infodir} \
	--libdir=%{common_libdir} \
	--disable-jemalloc \
	--disable-rpath \
	--disable-debuginfo-lines \
	--disable-debuginfo-only-std \
	--build=%{rust_triple} \
	--host=%{rust_triple} \
	--target=%{rust_triple} \
	--default-linker=gcc \
%if %{with llvm}
	--enable-llvm-link-shared \
	--llvm-root=%{_prefix} \
	--enable-clang \
%else
	--disable-clang \
	--disable-llvm-link-shared \
%endif
	--enable-optimize \
%if !%{with bootstrap}
	--enable-local-rust \
	--local-rust-root=%{_prefix} \
%endif
	--enable-vendor

# (tpg) build it
./x.py build

%install
DESTDIR=%{buildroot} ./x.py install
DESTDIR=%{buildroot} ./x.py install src

# Make sure the shared libraries are in the proper libdir
%if "%{_libdir}" != "%{common_libdir}"
mkdir -p %{buildroot}%{_libdir}
find %{buildroot}%{common_libdir} -maxdepth 1 -type f -name '*.so' \
  -exec mv -v -t %{buildroot}%{_libdir} '{}' '+'
%endif

# The shared libraries should be executable for debuginfo extraction.
find %{buildroot}%{_libdir} -maxdepth 1 -type f -name '*.so' \
  -exec chmod -v +x '{}' '+'

# The libdir libraries are identical to those under rustlib/.  It's easier on
# library loading if we keep them in libdir, but we do need them in rustlib/
# to support dynamic linking for compiler plugins, so we'll symlink.
(cd "%{buildroot}%{rustlibdir}/%{rust_triple}/lib" &&
 find ../../../../%{_lib} -maxdepth 1 -name '*.so' \
   -exec ln -v -f -s -t . '{}' '+')

# Remove installer artifacts (manifests, uninstall scripts, etc.)
find %{buildroot}%{rustlibdir} -maxdepth 1 -type f -exec rm -v '{}' '+'

# Manually strip them because auto-strip damages files
pushd %{buildroot}%{_libdir}
strip *.so
popd
pushd %{buildroot}%{_bindir}
strip rustc
strip rustdoc
popd

%files
%doc README.md
%{_bindir}/rustc
%{_bindir}/rustdoc
%{_bindir}/rust-gdb
%{_bindir}/rust-lldb
%{_libdir}/*.so
%dir %{rustlibdir}
%dir %{rustlibdir}/%{rust_triple}
%dir %{rustlibdir}/%{rust_triple}/lib
%{rustlibdir}/%{rust_triple}/lib/*.so
%{rustlibdir}/%{rust_triple}/lib/*.rlib
%dir %{rustlibdir}/etc
%{rustlibdir}/etc/*.py
%{_mandir}/man*/*

%files src
%dir %{rustlibdir}/src
%{rustlibdir}/src/*
