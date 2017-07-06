# Fix to work around missing (not required) dependency
# libpthread.so.0(GLIBC_PRIVATE)
%global __requires_exclude libpthread.so.0
%define debug_package %{nil}
%define _disable_lto 1
%define _disable_ld_no_undefined 1

%define oname	rustc

Summary:	A safe, concurrent, practical programming language
Name:		rust
Version:	1.18.0
Release:	1
Group:		Development/Other
License:	MIT
Url:		http://www.rust-lang.org/
Source0:	http://static.rust-lang.org/dist/%{oname}-%{version}-src.tar.gz
Source100:	rust.rpmlintrc
BuildRequires:	python < 3.0
BuildRequires:	cmake
# (tpg) LLVM support 4.0+ is not yet ready
# https://github.com/rust-lang/rust/issues/37609
BuildRequires:	curl
BuildRequires:	procps-ng
BuildRequires:	flex
BuildRequires:	bison
Provides:	%{oname} = %{EVRD}
# The C compiler is needed at runtime just for linking.  Someday rustc might
# invoke the linker directly, and then we'll only need binutils.
# https://github.com/rust-lang/rust/issues/11937
Requires:	gcc

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
rm -rf src/jemalloc/
%if %mdvver <= 201400
# (tpg) not yet ready
# rm -rf src/llvm/
%endif

%build
%setup_compile_flags
export CC=gcc
export CXX=g++
export RUST_BACKTRACE=1

# for some reason parts of the code still use cc call rather than the environment
# which results in a mixture
mkdir omv_build_comp
ln -s `which gcc` omv_build_comp/cc
export PATH=$PWD/omv_build_comp:$PATH

# Unable to use standard configure as rust's configure is missing
# many of the options as commented out below from the configure2_5x macro
./configure \
        --prefix=%{_prefix} \
        --sysconfdir=%{_sysconfdir} \
        --datadir=%{_datadir} \
        --localstatedir=%{_localstatedir} \
        --mandir=%{_mandir} \
        --infodir=%{_infodir} \
        --disable-rpath \
        --disable-jemalloc \
        --default-linker=gcc \
#       --build=%{_target_platform} \
#       --exec-prefix=%{_exec_prefix} \
#       --bindir=%{_bindir} \
#	--libdir=%{_libdir} \  # not properly supported
#       --sbindir=%{_sbindir} \
#       --includedir=%{_includedir} \
#       --libexecdir=%{_libexecdir} \
#       --sharedstatedir=%{_sharedstatedir} \

# cb strange results with parallel
make

%install
%makeinstall_std

# fix broken libdir on 64-bit
%if "%{_lib}" != "lib"
mv %{buildroot}/%{_prefix}/lib %{buildroot}/%{_libdir}
%endif

%files
%{_bindir}/rustc
%{_bindir}/rustdoc
%{_bindir}/rust-gdb
%{_bindir}/rust-lldb
%{_libdir}/rustlib
%{_libdir}/lib*
%{_mandir}/man*/*
%{_docdir}/%{name}
