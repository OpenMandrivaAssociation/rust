# Fix to work around missing (not required) dependency
# libpthread.so.0(GLIBC_PRIVATE)
%global __requires_exclude libpthread.so.0

Summary:	A safe, concurrent, practical programming language
Name:		rust
Version:	0.10
Release:	%mkrel 4
Source0:	http://static.rust-lang.org/dist/%{name}-%{version}.tar.gz
License:	MIT
Group:		Development/Other
Url:		http://www.rust-lang.org/

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

%package -n vim-rust
Group:          Editors
Summary:        Syntax highlighting for rust in vim

%description -n vim-rust
The vim-rust package provides filetype detection and syntax highlighting for
the rust programming language.

%package -n kate-rust
Group:          Editors
Summary:        Syntax highlighting for rust in kate

%description -n kate-rust
The kate-rust package provides filetype detection and syntax highlighting for
the rust programming language.

%prep
%setup -q

%build
# enable better rust debug messages during build
export RUST_LOG=rustc=1;

# Unable to use standard configure as rust's configure is missing
# many of the options as commented out below from the configure2_5x macro
# build opt is available, but the mageia specific target platform is supported
./configure \
        --prefix=%{_prefix} \
        --sysconfdir=%{_sysconfdir} \
        --datadir=%{_datadir} \
        --libdir=%{_libdir} \
        --localstatedir=%{_localstatedir} \
        --mandir=%{_mandir} \
        --infodir=%{_infodir}

#       --build=%{_target_platform} \
#       --exec-prefix=%{_exec_prefix} \
#       --bindir=%{_bindir} \
#       --sbindir=%{_sbindir} \
#       --includedir=%{_includedir} \
#       --libexecdir=%{_libexecdir} \
#       --sharedstatedir=%{_sharedstatedir} \

%make

%install
%makeinstall_std

# vim syntax files
vimdir=%{buildroot}%{_datadir}/vim
mkdir -vp %{buildroot}%{_datadir}/vim
cp -vr src/etc/vim/* $vimdir/

# kate syntax files
mkdir -vp %{buildroot}%{_datadir}/apps/katepart/syntax/
cp -v src/etc/kate/rust.xml %{buildroot}%{_datadir}/apps/katepart/syntax/

%files
%{_bindir}/rustc
%{_bindir}/rustdoc
%{_libdir}/rustlib
%{_libdir}/lib*
%{_mandir}/man*/*

%files -n vim-rust
%{_datadir}/vim/*

%files -n kate-rust
%{_datadir}/apps/katepart/syntax/rust.xml


%changelog
* Wed Oct 15 2014 umeabot <umeabot> 0.10-4.mga5
+ Revision: 747079
- Second Mageia 5 Mass Rebuild

* Tue Sep 16 2014 umeabot <umeabot> 0.10-3.mga5
+ Revision: 689010
- Mageia 5 Mass Rebuild

  + tv <tv>
    - use %%global for req/prov exclude
    - autoconvert to new prov/req excludes

* Fri Apr 25 2014 thatsamguy <thatsamguy> 0.10-2.mga5
+ Revision: 617730
- fix libpthread.so.0 dependency issues

* Fri Apr 25 2014 thatsamguy <thatsamguy> 0.10-1.mga5
+ Revision: 617721
- update to latest release v0.10

* Sat Feb 15 2014 thatsamguy <thatsamguy> 0.9-1.mga5
+ Revision: 591692
- update to latest stable release v0.9

* Mon Oct 21 2013 umeabot <umeabot> 0.8-2.mga4
+ Revision: 541162
- Mageia 4 Mass Rebuild

* Thu Oct 10 2013 thatsamguy <thatsamguy> 0.8-1.mga4
+ Revision: 494701
- fix build error from macro in comments
- imported package rust

