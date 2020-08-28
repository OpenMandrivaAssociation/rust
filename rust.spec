%define _disable_lto 1

# Only x86_64 and i686 are Tier 1 platforms at this time.
# https://forge.rust-lang.org/platform-support.html
%global rust_arches x86_64 znver1 i686 armv7hl armv7hnl aarch64 ppc64 ppc64le s390x

# The channel can be stable, beta, or nightly
%{!?channel: %global channel stable}

# To bootstrap from scratch, set the channel and date from src/stage0.txt
# e.g. 1.10.0 wants rustc: 1.9.0-2016-05-24
# or nightly wants some beta-YYYY-MM-DD
# Note that cargo matches the program version here, not its crate version.
%global bootstrap_rust 1.46.0
%global bootstrap_cargo 1.46.0
%global bootstrap_channel 1.46.0

# Only the specified arches will use bootstrap binaries.
%global bootstrap_arches %%{rust_arches}

# Using llvm-static may be helpful as an opt-in, e.g. to aid LLVM rebases.
%bcond_with llvm_static

# We can also choose to just use Rust's bundled LLVM, in case the system LLVM
# is insufficient.  Rust currently requires LLVM 7.0+.
%bcond_with bundled_llvm

# libgit2-sys expects to use its bundled library, which is sometimes just a
# snapshot of libgit2's master branch.  This can mean the FFI declarations
# won't match our released libgit2.so, e.g. having changed struct fields.
# So, tread carefully if you toggle this...
%bcond_without bundled_libgit2
%bcond_with bundled_libssh2

# LLDB isn't available everywhere...
%bcond_without lldb

Name:           rust
Version:        1.46.0
Release:        1
Summary:        The Rust Programming Language
License:        (ASL 2.0 or MIT) and (BSD and MIT)
# ^ written as: (rust itself) and (bundled libraries)
URL:            https://www.rust-lang.org
ExclusiveArch:  %{rust_arches}

%if "%{channel}" == "stable"
%global rustc_package rustc-%{version}-src
%else
%global rustc_package rustc-%{channel}-src
%endif
Source0:        https://static.rust-lang.org/dist/%{rustc_package}.tar.xz
# update from openssl-300 branch at https://github.com/sfackler/rust-openssl
Source100:	openssl3.tar.gz
# Revert https://github.com/rust-lang/rust/pull/57840
# We do have the necessary fix in our LLVM 7.
Patch1:         rust-pr57840-llvm7-debuginfo-variants.patch
Patch2:		rust-pr70163-prepare-for-llvm-10-upgrade.patch
%{lua: function rust_triple(arch)
  local abi = "gnu"
  if arch == "armv7hnl" then
    arch = "armv7"
    abi = "gnueabihf"
  elseif arch == "armv7hl" then
    arch = "armv7"
    abi = "gnueabihf"
  elseif arch == "ppc64" then
    arch = "powerpc64"
  elseif arch == "ppc64le" then
    arch = "powerpc64le"
  elseif arch == "i586" then
    arch = "i686"
  elseif arch == "znver1" then
    arch = "x86_64"
  end
  return arch.."-unknown-linux-"..abi
end}

%global rust_triple %{lua: print(rust_triple(rpm.expand("%{_target_cpu}")))}

%if %defined bootstrap_arches
# For each bootstrap arch, add an additional binary Source.
# Also define bootstrap_source just for the current target.
%{lua: do
  local bootstrap_arches = {}
  for arch in string.gmatch(rpm.expand("%{bootstrap_arches}"), "%S+") do
    table.insert(bootstrap_arches, arch)
  end
  local base = rpm.expand("https://static.rust-lang.org/dist"
                          .."/rust-%{bootstrap_channel}")
  local target_arch = rpm.expand("%{_target_cpu}")
  for i, arch in ipairs(bootstrap_arches) do
    print(string.format("Source%d: %s-%s.tar.gz\n",
                        i, base, rust_triple(arch)))
    if arch == target_arch then
      rpm.define("bootstrap_source "..i)
    end
  end
end}
%endif

%ifarch %{bootstrap_arches}
%global bootstrap_root rust-%{bootstrap_channel}-%{rust_triple}
%global local_rust_root %{_builddir}/%{bootstrap_root}/usr
Provides:       bundled(%{name}-bootstrap) = %{bootstrap_rust}
%else
BuildRequires:  cargo >= %{bootstrap_cargo}
BuildRequires:  (%{name} >= %{bootstrap_rust} with %{name} <= %{version})
%global local_rust_root %{_prefix}
%endif

BuildRequires:  make
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  ncurses-devel
BuildRequires:  curl
BuildRequires:  pkgconfig(libcurl)
BuildRequires:  pkgconfig(liblzma)
BuildRequires:  pkgconfig(openssl)
BuildRequires:  pkgconfig(zlib)

%if %without bundled_libgit2
BuildRequires:  pkgconfig(libgit2) >= 0.27
%endif

%if %without bundled_libssh2
# needs libssh2_userauth_publickey_frommemory
BuildRequires:  pkgconfig(libssh2) >= 1.6.0
%endif

%global python python3
BuildRequires:  %{python}

%if %with bundled_llvm
BuildRequires:  cmake >= 3.4.3
Provides:       bundled(llvm) = 9.0.0
%else
BuildRequires:  cmake >= 2.8.11
%global llvm llvm
%global llvm_root %{_prefix}
BuildRequires:  %{llvm}-devel >= 7.0
%if %with llvm_static
BuildRequires:  %{llvm}-static
BuildRequires:  libffi-devel
%endif
%endif

# make check needs "ps" for src/test/run-pass/wait-forked-but-failed-child.rs
BuildRequires:  procps-ng

# debuginfo-gdb tests need gdb
BuildRequires:  gdb

# TODO: work on unbundling these!
Provides:       bundled(libbacktrace) = 8.1.0
Provides:       bundled(miniz) = 2.0.7

# Virtual provides for folks who attempt "dnf install rustc"
Provides:       rustc = %{version}-%{release}
Provides:       rustc%{?_isa} = %{version}-%{release}

# Always require our exact standard library
Requires:       %{name}-std-static%{?_isa} = %{version}-%{release}

# The C compiler is needed at runtime just for linking.  Someday rustc might
# invoke the linker directly, and then we'll only need binutils.
# https://github.com/rust-lang/rust/issues/11937
Requires:       /usr/bin/cc

# ALL Rust libraries are private, because they don't keep an ABI.
%global _privatelibs lib(.*-[[:xdigit:]]{16}*|rustc.*)[.]so.*
%global __provides_exclude ^(%{_privatelibs})$
%global __requires_exclude ^(%{_privatelibs})$
%global __provides_exclude_from ^(%{_docdir}|%{rustlibdir}/src)/.*$
%global __requires_exclude_from ^(%{_docdir}|%{rustlibdir}/src)/.*$

# We need the unallocated metadata (.rustc) to
# support custom-derive plugins like #[proc_macro_derive(Foo)].
%global _find_debuginfo_opts --keep-section .rustc

# Use hardening ldflags.
%global rustflags -Clink-arg=-Wl,-z,relro,-z,now

%if %{without bundled_llvm}
%if "%{llvm_root}" == "%{_prefix}" || 0%{?scl:1}
%global llvm_has_filecheck 1
%endif
%endif

%description
Rust is a systems programming language that runs blazingly fast, prevents
segfaults, and guarantees thread safety.

This package includes the Rust compiler and documentation generator.


%package std-static
Summary:        Standard library for Rust

%description std-static
This package includes the standard libraries for building applications
written in Rust.


%package debugger-common
Summary:        Common debugger pretty printers for Rust
BuildArch:      noarch

%description debugger-common
This package includes the common functionality for %{name}-gdb and %{name}-lldb.


%package gdb
Summary:        GDB pretty printers for Rust
BuildArch:      noarch
Requires:       gdb
Requires:       %{name}-debugger-common = %{version}-%{release}

%description gdb
This package includes the rust-gdb script, which allows easier debugging of Rust
programs.


%if %with lldb

%package lldb
Summary:        LLDB pretty printers for Rust
BuildArch:      noarch
Requires:       lldb
Requires:       %{name}-debugger-common = %{version}-%{release}

%description lldb
This package includes the rust-lldb script, which allows easier debugging of Rust
programs.

%endif


%package doc
Summary:        Documentation for Rust
# NOT BuildArch:      noarch
# Note, while docs are mostly noarch, some things do vary by target_arch.
# Koji will fail the build in rpmdiff if two architectures build a noarch
# subpackage differently, so instead we have to keep its arch.

%description doc
This package includes HTML documentation for the Rust programming language and
its standard library.


%package -n cargo
Summary:        Rust's package manager and build tool
%if %with bundled_libgit2
Provides:       bundled(libgit2) = 0.28.2
%endif
%if %with bundled_libssh2
Provides:       bundled(libssh2) = 1.8.1~dev
%endif
# For tests:
BuildRequires:  git
# Cargo is not much use without Rust
Requires:       rust

# "cargo vendor" is a builtin command starting with 1.37.  The Obsoletes and
# Provides are mostly relevant to RHEL, but harmless to have on Fedora/etc. too
Obsoletes:      cargo-vendor <= 0.1.23
Provides:       cargo-vendor = %{version}-%{release}

%description -n cargo
Cargo is a tool that allows Rust projects to declare their various dependencies
and ensure that you'll always get a repeatable build.


%package -n cargo-doc
Summary:        Documentation for Cargo
BuildArch:      noarch
# Cargo no longer builds its own documentation
# https://github.com/rust-lang/cargo/pull/4904
Requires:       rust-doc = %{version}-%{release}

%description -n cargo-doc
This package includes HTML documentation for Cargo.


%package -n rustfmt
Summary:        Tool to find and fix Rust formatting issues
Requires:       cargo

# The component/package was rustfmt-preview until Rust 1.31.
Obsoletes:      rustfmt-preview < 1.0.0
Provides:       rustfmt-preview = %{version}-%{release}

%description -n rustfmt
A tool for formatting Rust code according to style guidelines.


%package -n rls
Summary:        Rust Language Server for IDE integration
%if %with bundled_libgit2
Provides:       bundled(libgit2) = 0.28.2
%endif
%if %with bundled_libssh2
Provides:       bundled(libssh2) = 1.8.1~dev
%endif
Requires:       rust-analysis
# /usr/bin/rls is dynamically linked against internal rustc libs
Requires:       %{name}%{?_isa} = %{version}-%{release}

# The component/package was rls-preview until Rust 1.31.
Obsoletes:      rls-preview < 1.31.6
Provides:       rls-preview = %{version}-%{release}

%description -n rls
The Rust Language Server provides a server that runs in the background,
providing IDEs, editors, and other tools with information about Rust programs.
It supports functionality such as 'goto definition', symbol search,
reformatting, and code completion, and enables renaming and refactorings.


%package -n clippy
Summary:        Lints to catch common mistakes and improve your Rust code
Requires:       cargo
# /usr/bin/clippy-driver is dynamically linked against internal rustc libs
Requires:       %{name}%{?_isa} = %{version}-%{release}

# The component/package was clippy-preview until Rust 1.31.
Obsoletes:      clippy-preview <= 0.0.212
Provides:       clippy-preview = %{version}-%{release}

%description -n clippy
A collection of lints to catch common mistakes and improve your Rust code.


%package src
Summary:        Sources for the Rust standard library
BuildArch:      noarch

%description src
This package includes source files for the Rust standard library.  It may be
useful as a reference for code completion tools in various editors.


%package analysis
Summary:        Compiler analysis data for the Rust standard library
Requires:       rust-std-static%{?_isa} = %{version}-%{release}

%description analysis
This package contains analysis data files produced with rustc's -Zsave-analysis
feature for the Rust standard library. The RLS (Rust Language Server) uses this
data to provide information about the Rust standard library.


%prep

%ifarch %{bootstrap_arches}
%setup -q -n %{bootstrap_root} -T -b %{bootstrap_source}
./install.sh --components=cargo,rustc,rust-std-%{rust_triple} \
  --prefix=%{local_rust_root} --disable-ldconfig
test -f '%{local_rust_root}/bin/cargo'
test -f '%{local_rust_root}/bin/rustc'
%endif

%setup -q -n %{rustc_package}

#patch1 -p1 -R
#patch2 -p1
pushd vendor
rm -Rf openssl openssl-sys
tar xvf %SOURCE100
sed -i -e 's/0.10.25/0.10.30/' -e 's/0.9.54/0.9.58/' ../Cargo.lock
popd

%if "%{python}" == "python3"
sed -i.try-py3 -e '/try python2.7/i try python3 "$@"' ./configure
%endif

%if %without bundled_llvm
rm -rf src/llvm-project/
%endif

# Remove other unused vendored libraries
rm -rf vendor/curl-sys/curl/
rm -rf vendor/jemalloc-sys/jemalloc/
rm -rf vendor/libz-sys/src/zlib/
rm -rf vendor/lzma-sys/xz-*/
rm -rf vendor/openssl-src/openssl/

%if %without bundled_libgit2
rm -rf vendor/libgit2-sys/libgit2/
%endif

%if %without bundled_libssh2
rm -rf vendor/libssh2-sys/libssh2/
%endif

# This only affects the transient rust-installer, but let it use our dynamic xz-libs
sed -i.lzma -e '/LZMA_API_STATIC/d' src/bootstrap/tool.rs

# rename bundled license for packaging
cp -a vendor/backtrace-sys/src/libbacktrace/LICENSE{,-libbacktrace}

%if %{with bundled_llvm} && 0%{?epel}
mkdir -p cmake-bin
ln -s /usr/bin/cmake3 cmake-bin/cmake
%global cmake_path $PWD/cmake-bin
%endif

%if %{without bundled_llvm} && %{with llvm_static}
# Static linking to distro LLVM needs to add -lffi
# https://github.com/rust-lang/rust/issues/34486
sed -i.ffi -e '$a #[link(name = "ffi")] extern {}' \
  src/librustc_llvm/lib.rs
%endif

# The configure macro will modify some autoconf-related files, which upsets
# cargo when it tries to verify checksums in those files.  If we just truncate
# that file list, cargo won't have anything to complain about.
find vendor -name .cargo-checksum.json \
  -exec sed -i.uncheck -e 's/"files":{[^}]*}/"files":{ }/' '{}' '+'

# Sometimes Rust sources start with #![...] attributes, and "smart" editors think
# it's a shebang and make them executable. Then brp-mangle-shebangs gets upset...
find -name '*.rs' -type f -perm /111 -exec chmod -v -x '{}' '+'


%build
%if %without bundled_libgit2
# convince libgit2-sys to use the distro libgit2
export LIBGIT2_SYS_USE_PKG_CONFIG=1
%endif

%if %without bundled_libssh2
# convince libssh2-sys to use the distro libssh2
export LIBSSH2_SYS_USE_PKG_CONFIG=1
%endif

%{?cmake_path:export PATH=%{cmake_path}:$PATH}
%{?rustflags:export RUSTFLAGS="%{rustflags}"}

# We're going to override --libdir when configuring to get rustlib into a
# common path, but we'll fix the shared libraries during install.
%global common_libdir %{_prefix}/lib
%global rustlibdir %{common_libdir}/rustlib

%ifarch %{arm} %{ix86} s390x
# full debuginfo is exhausting memory; just do libstd for now
# https://github.com/rust-lang/rust/issues/45854
%define enable_debuginfo --debuginfo-level=0 --debuginfo-level-std=2
%else
%define enable_debuginfo --debuginfo-level=2
%endif

# We want the best optimization for std, but it caused problems for rpm-ostree
# on ppc64le to have all of the compiler_builtins in a single object:
# https://bugzilla.redhat.com/show_bug.cgi?id=1713090
%ifnarch %{power64}
%define codegen_units_std --set rust.codegen-units-std=1
%endif

%configure --disable-option-checking \
  --libdir=%{common_libdir} \
  --build=%{rust_triple} --host=%{rust_triple} --target=%{rust_triple} \
  --python=%{python} \
  --local-rust-root=%{local_rust_root} \
  %{!?with_bundled_llvm: --llvm-root=%{llvm_root} \
  %{!?llvm_has_filecheck: --disable-codegen-tests} \
  %{!?with_llvm_static: --enable-llvm-link-shared } } \
  --disable-rpath \
  %{enable_debuginfo} \
  --enable-extended \
  --tools=analysis,cargo,clippy,rls,rustfmt,src \
  --enable-vendor \
  --enable-verbose-tests \
  %{?codegen_units_std} \
  --release-channel=%{channel}

%{python} ./x.py build
%{python} ./x.py doc


%install
%{?cmake_path:export PATH=%{cmake_path}:$PATH}
%{?rustflags:export RUSTFLAGS="%{rustflags}"}

DESTDIR=%{buildroot} %{python} ./x.py install

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
 find ../../../../%{_lib} -maxdepth 1 -name '*.so' |
 while read lib; do
   if [ -f "${lib##*/}" ]; then
     # make sure they're actually identical!
     cmp "$lib" "${lib##*/}"
     ln -v -f -s -t . "$lib"
   fi
 done)

# Remove installer artifacts (manifests, uninstall scripts, etc.)
find %{buildroot}%{rustlibdir} -maxdepth 1 -type f -exec rm -v '{}' '+'

# Remove backup files from %%configure munging
find %{buildroot}%{rustlibdir} -type f -name '*.orig' -exec rm -v '{}' '+'

# https://fedoraproject.org/wiki/Changes/Make_ambiguous_python_shebangs_error
# We don't actually need to ship any of those python scripts in rust-src anyway.
find %{buildroot}%{rustlibdir}/src -type f -name '*.py' -exec rm -v '{}' '+'

# FIXME: __os_install_post will strip the rlibs
# -- should we find a way to preserve debuginfo?

# Remove unwanted documentation files (we already package them)
rm -f %{buildroot}%{_docdir}/%{name}/README.md
rm -f %{buildroot}%{_docdir}/%{name}/COPYRIGHT
rm -f %{buildroot}%{_docdir}/%{name}/LICENSE
rm -f %{buildroot}%{_docdir}/%{name}/LICENSE-APACHE
rm -f %{buildroot}%{_docdir}/%{name}/LICENSE-MIT
rm -f %{buildroot}%{_docdir}/%{name}/LICENSE-THIRD-PARTY
rm -f %{buildroot}%{_docdir}/%{name}/*.old

# Sanitize the HTML documentation
find %{buildroot}%{_docdir}/%{name}/html -empty -delete
find %{buildroot}%{_docdir}/%{name}/html -type f -exec chmod -x '{}' '+'

# Create the path for crate-devel packages
mkdir -p %{buildroot}%{_datadir}/cargo/registry

# Cargo no longer builds its own documentation
# https://github.com/rust-lang/cargo/pull/4904
mkdir -p %{buildroot}%{_docdir}/cargo
ln -sT ../rust/html/cargo/ %{buildroot}%{_docdir}/cargo/html

%if %without lldb
rm -f %{buildroot}%{_bindir}/rust-lldb
rm -f %{buildroot}%{rustlibdir}/etc/lldb_*.py*
%endif


%check
%{?cmake_path:export PATH=%{cmake_path}:$PATH}
%{?rustflags:export RUSTFLAGS="%{rustflags}"}

# The results are not stable on koji, so mask errors and just log it.
%{python} ./x.py test --no-fail-fast || :
%{python} ./x.py test --no-fail-fast cargo || :
%{python} ./x.py test --no-fail-fast clippy || :
%{python} ./x.py test --no-fail-fast rls || :
%{python} ./x.py test --no-fail-fast rustfmt || :


%files
%license COPYRIGHT LICENSE-APACHE LICENSE-MIT
%license vendor/backtrace-sys/src/libbacktrace/LICENSE-libbacktrace
%doc README.md
%{_bindir}/rustc
%{_bindir}/rustdoc
%{_libdir}/*.so
%{_mandir}/man1/rustc.1*
%{_mandir}/man1/rustdoc.1*
%dir %{rustlibdir}
%dir %{rustlibdir}/%{rust_triple}
%dir %{rustlibdir}/%{rust_triple}/lib
%{rustlibdir}/%{rust_triple}/lib/*.so


%files std-static
%dir %{rustlibdir}
%dir %{rustlibdir}/%{rust_triple}
%dir %{rustlibdir}/%{rust_triple}/lib
%{rustlibdir}/%{rust_triple}/lib/*.rlib


%files debugger-common
%dir %{rustlibdir}
%dir %{rustlibdir}/etc
%{rustlibdir}/etc/rust_types.py


%files gdb
%{_bindir}/rust-gdb
%{rustlibdir}/etc/gdb_*.py*
%exclude %{_bindir}/rust-gdbgui


%if %with lldb
%files lldb
%{_bindir}/rust-lldb
%{rustlibdir}/etc/lldb_*.py*
%endif


%files doc
%docdir %{_docdir}/%{name}
%dir %{_docdir}/%{name}
%dir %{_docdir}/%{name}/html
%{_docdir}/%{name}/html/*/
%{_docdir}/%{name}/html/*.html
%{_docdir}/%{name}/html/*.css
%{_docdir}/%{name}/html/*.ico
%{_docdir}/%{name}/html/*.js
%{_docdir}/%{name}/html/*.png
%{_docdir}/%{name}/html/*.svg
%{_docdir}/%{name}/html/*.woff
%license %{_docdir}/%{name}/html/*.txt
%license %{_docdir}/%{name}/html/*.md


%files -n cargo
%license src/tools/cargo/LICENSE-APACHE src/tools/cargo/LICENSE-MIT src/tools/cargo/LICENSE-THIRD-PARTY
%doc src/tools/cargo/README.md
%{_bindir}/cargo
%{_mandir}/man1/cargo*.1*
%{_sysconfdir}/bash_completion.d/cargo
%{_datadir}/zsh/site-functions/_cargo
%dir %{_datadir}/cargo
%dir %{_datadir}/cargo/registry


%files -n cargo-doc
%docdir %{_docdir}/cargo
%dir %{_docdir}/cargo
%{_docdir}/cargo/html


%files -n rustfmt
%{_bindir}/rustfmt
%{_bindir}/cargo-fmt
%doc src/tools/rustfmt/{README,CHANGELOG,Configurations}.md
%license src/tools/rustfmt/LICENSE-{APACHE,MIT}


%files -n rls
%{_bindir}/rls
%doc src/tools/rls/{README.md,COPYRIGHT,debugging.md}
%license src/tools/rls/LICENSE-{APACHE,MIT}


%files -n clippy
%{_bindir}/cargo-clippy
%{_bindir}/clippy-driver
%doc src/tools/clippy/{README.md,CHANGELOG.md}
%license src/tools/clippy/LICENSE-{APACHE,MIT}


%files src
%dir %{rustlibdir}
%{rustlibdir}/src


%files analysis
%{rustlibdir}/%{rust_triple}/analysis/
