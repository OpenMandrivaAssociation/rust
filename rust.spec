# Fix to work around missing (not required) dependency
# libpthread.so.0(GLIBC_PRIVATE)
%global __requires_exclude libpthread.so.0
%define debug_package %{nil}
%define _disable_lto 1
%define _disable_ld_no_undefined 1
# To avoid undefined symbols
%define _find_debuginfo_opts -g

%bcond_without bootstrap
%define oname	rustc

# Only x86_64 and i686 are Tier 1 platforms at this time.
# https://forge.rust-lang.org/platform-support.html
%global rust_arches x86_64 %ix86 armv7hl aarch64

Summary:	A safe, concurrent, practical programming language
Name:		rust
Version:	1.21.0
Release:	1
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
BuildRequires:	llvm-devel
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

%prep
%setup -q -n %{oname}-%{version}-src

# (tpg) not needed
rm -rf src/llvm/
rm -rf src/jemalloc/

%build
%setup_compile_flags
%if 1
export CC=/usr/bin/gcc
export CXX=/usr/bin/g++
%endif
export RUST_BACKTRACE=1

# for some reason parts of the code still use cc call rather than the environment
# which results in a mixture
%if 1
mkdir omv_build_comp
ln -s `which gcc` omv_build_comp/cc
ln -s `which g++` omv_build_comp/g++
export PATH=$PWD/omv_build_comp:$PATH
%endif

# Unable to use standard configure as rust's configure is missing
# many of the options as commented out below from the configure2_5x macro
./configure \
        --prefix=%{_prefix} \
        --sysconfdir=%{_sysconfdir} \
        --datadir=%{_datadir} \
        --localstatedir=%{_localstatedir} \
        --mandir=%{_mandir} \
        --infodir=%{_infodir} \
	--libdir=%{_prefix}/lib \
	--disable-jemalloc \
        --disable-rpath \
	--build=%{rust_triple} \
	--host=%{rust_triple} \
	--target=%{rust_triple} \
        --default-linker=gcc \
        --enable-llvm-link-shared \
        --llvm-root=%{_prefix} \
	--enable-optimize \
	--disable-clang \
%if !%{with bootstrap}
	--enable-local-rust \
	--local-rust-root=%{_prefix} \
%endif
        --enable-vendor

# cb strange results with parallel
#make
./x.py build --verbose

%install
%makeinstall_std

# fix broken libdir on 64-bit
%if "%{_lib}" != "lib"
mv %{buildroot}/%{_prefix}/lib %{buildroot}/%{_libdir}
%endif

# Turn libraries into symlinks to avoid duplicate Provides
pushd %{buildroot}%{_libdir}/rustlib/*/lib/
rm lib*.so
for lib in ../../../*.so
do
	ln -s $lib `basename $lib`
done
popd

# Manually strip them because auto-strip damages files
pushd %{buildroot}%{_libdir}
strip *.so
popd
pushd %{buildroot}%{_bindir}
strip rustc
strip rustdoc
popd

%files
%{_bindir}/rustc
%{_bindir}/rustdoc
%{_bindir}/rust-gdb
%{_bindir}/rust-lldb
%{_libdir}/rustlib
%{_libdir}/lib*
%{_mandir}/man*/*
%{_docdir}/%{name}
