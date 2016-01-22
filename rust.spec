# Fix to work around missing (not required) dependency
# libpthread.so.0(GLIBC_PRIVATE)
%global __requires_exclude libpthread.so.0
%define debug_package %{nil}

%define oname	rustc

Summary:	A safe, concurrent, practical programming language
Name:		rust
Version:	1.6.0
Release:	1
Source0:	http://static.rust-lang.org/dist/%{oname}-%{version}-src.tar.gz
Source100:	rust.rpmlintrc
License:	MIT
Group:		Development/Other
Url:		http://www.rust-lang.org/
Provides:	%{oname}

BuildRequires:  python < 3.0

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
%setup -q -n %{oname}-%{version}

%build
# enable better rust debug messages during build
export RUST_LOG=rustc=1;

# Unable to use standard configure as rust's configure is missing
# many of the options as commented out below from the configure2_5x macro
./configure \
        --prefix=%{_prefix} \
        --sysconfdir=%{_sysconfdir} \
        --datadir=%{_datadir} \
        --localstatedir=%{_localstatedir} \
        --mandir=%{_mandir} \
        --infodir=%{_infodir}

#       --build=%{_target_platform} \
#       --exec-prefix=%{_exec_prefix} \
#       --bindir=%{_bindir} \
#	--libdir=%{_libdir} \  # not properly supported
#       --sbindir=%{_sbindir} \
#       --includedir=%{_includedir} \
#       --libexecdir=%{_libexecdir} \
#       --sharedstatedir=%{_sharedstatedir} \

%make

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
%{_libdir}/rustlib
%{_libdir}/lib*
%{_mandir}/man*/*
%{_docdir}/%{name}
