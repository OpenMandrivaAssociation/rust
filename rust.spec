%define _disable_lto 1
%define _disable_ld_no_undefined 1

# Only x86_64 and i686 are Tier 1 platforms at this time.
# https://forge.rust-lang.org/platform-support.html
%global rust_arches x86_64 znver1 i686 armv7hl armv7hnl aarch64 ppc64 ppc64le riscv64

# The channel can be stable, beta, or nightly
%{!?channel: %global channel stable}

# To bootstrap from scratch, set the channel and date from src/stage0.json
# e.g. 1.10.0 wants rustc: 1.9.0-2016-05-24
# or nightly wants some beta-YYYY-MM-DD
# Note that cargo matches the program version here, not its crate version.
%global bootstrap_rust 1.87.0
%global bootstrap_cargo 1.87.0
%global bootstrap_channel 1.87.0

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

# Running the tests uses loads of diskspace -- causing various abf buildroots
# to run out of space
%bcond_with tests

Name:           rust
Version:        1.88.0
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
# Remove lock file check, it breaks vendoring tagged git
# (see amdgpu_top package)
Patch0:		rust-1.74.0-cargo-drop-lockfile-check.patch
Patch1:		rust-1.80-ldflags.patch
#Patch2:    0001-Fix-profiler_builtins-build-script-to-handle-full-pa.patch
Patch3:		https://github.com/rust-lang/rust/pull/143684.patch
Patch4:		https://github.com/rust-lang/rust/pull/143255.patch

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
  elseif arch == "riscv64" then
    arch = "riscv64gc"
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
    -- rust doesn't make a difference between x86_64/znver1 or armv7hl/armv7hnl
    -- don't add the same source twice
    if arch~="znver1" and arch~="armv7hl" then
      print(string.format("Source%d: %s-%s.tar.xz\n",
                          i, base, rust_triple(arch)))
      if arch == target_arch or (target_arch=="znver1" and arch=="x86_64") or (target_arch=="armv7hl" and arch=="armv7hnl") then
        rpm.define("bootstrap_source "..i)
      end
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
BuildRequires:  pkgconfig(ncursesw)
BuildRequires:  curl
BuildRequires:  pkgconfig(libcurl)
BuildRequires:  pkgconfig(liblzma)
BuildRequires:  pkgconfig(openssl)
BuildRequires:  pkgconfig(zlib)
BuildRequires:  stdc++-static-devel
BuildRequires:  stdc++-devel

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
BuildRequires:  ninja
Provides:       bundled(llvm) = 15.0.0
%else
BuildRequires:  cmake >= 2.8.11
%global llvm llvm
%global llvm_root %{_prefix}
BuildRequires:  %{llvm}-devel >= 15.0
BuildRequires:  cmake(Polly)
%if %with llvm_static
BuildRequires:  %{llvm}-static
BuildRequires:  pkgconfig(libffi)
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

#package analysis
#Summary:        Compiler analysis data for the Rust standard library
#Requires:       rust-std-static%{?_isa} = %{version}-%{release}
#Obsoletes:      rls < 1.65.0

#description analysis
#This package contains analysis data files produced with rustc's -Zsave-analysis
#feature for the Rust standard library. The RLS (Rust Language Server) uses this
#data to provide information about the Rust standard library.

%prep

%ifarch %{bootstrap_arches}
%setup -q -n %{bootstrap_root} -T -b %{bootstrap_source}
./install.sh --components=cargo,rustc,rust-std-%{rust_triple} \
  --prefix=%{local_rust_root} --disable-ldconfig
test -f '%{local_rust_root}/bin/cargo'
test -f '%{local_rust_root}/bin/rustc'
%endif

%autosetup -p1 -n %{rustc_package}

%if %without bundled_llvm
rm -rf src/llvm-project/
mkdir -p src/llvm-project/libunwind/
%endif

# Remove other unused vendored libraries
rm -rf vendor/curl-sys/curl/
rm -rf vendor/*jemalloc-sys*/jemalloc/
rm -rf vendor/libmimalloc-sys/c_src/mimalloc/
rm -rf vendor/libz-sys/src/zlib/
rm -rf vendor/libz-sys/src/zlib-ng/
rm -rf vendor/lzma-sys/xz-*/
rm -rf vendor/openssl-src/openssl/

%if %without bundled_libgit2
rm -rf vendor/libgit2-sys/libgit2/
%endif

%if %without bundled_libssh2
rm -rf vendor/libssh2-sys/libssh2/
%endif

# This only affects the transient rust-installer, but let it use our dynamic xz-libs
sed -i.lzma -e '/LZMA_API_STATIC/d' src/bootstrap/src/core/build_steps/tool.rs

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
%ifarch znver1
# builder runs out of space causing rpm to be unable to correctly produce requires
%define enable_debuginfo --debuginfo-level=0 --debuginfo-level-std=2
%else
%define enable_debuginfo --debuginfo-level=2
%endif
%endif

# We want the best optimization for std, but it caused problems for rpm-ostree
# on ppc64le to have all of the compiler_builtins in a single object:
# https://bugzilla.redhat.com/show_bug.cgi?id=1713090
%ifnarch %{power64}
%define codegen_units_std --set rust.codegen-units-std=1
%endif

%if %{with bundled_llvm}
export CC="gcc -fuse-ld=lld"
export CXX="g++ -fuse-ld=lld"
export max_cpus=4
%global optflags %{optflags} -g0
%else
export max_cpus=4
%endif

%configure --disable-option-checking \
  --libdir=%{common_libdir} \
  --build=%{rust_triple} --host=%{rust_triple} --target=%{rust_triple} \
  --set target.%{rust_triple}.linker="%{__cc}" \
  --set target.%{rust_triple}.cc="%{__cc}" \
  --set target.%{rust_triple}.cxx="%{__cxx}" \
  --set target.%{rust_triple}.ar="%{__ar}" \
  --set target.%{rust_triple}.ranlib="%{__ranlib}" \
  --set target.%{rust_triple}.profiler="$(ls %{_libdir}/clang/*/lib/%{_arch}-*-linux%{_gnu}/libclang_rt.profile.a |head -n1)" \
  --set build.optimized-compiler-builtins=false \
  --python=%{python} \
  --local-rust-root=%{local_rust_root} \
  %{!?with_bundled_llvm: --llvm-root=%{llvm_root} --llvm-config=%{_bindir}/llvm-config \
  %{!?llvm_has_filecheck: --disable-codegen-tests} \
  %{!?with_llvm_static: --enable-llvm-link-shared } } \
  --disable-llvm-static-stdcpp \
  %{enable_debuginfo} \
  --enable-extended \
  --tools=cargo,clippy,rls,rust-analyzer,rustfmt,src \
  --enable-vendor \
  --enable-verbose-tests \
  --dist-compression-formats=gz,xz \
  %{?codegen_units_std} \
  --release-channel=%{channel} \
  --release-description="OpenMandriva %{version}-%{release}" \
  --enable-rpath

cpus=$(nproc)


if [[ $cpus -gt $max_cpus ]]; then
  cpus=$max_cpus
fi

%{python} ./x.py build -j "$cpus"
%{python} ./x.py doc


%install
# Make sure we can see librustc_driver-*.so
export LD_LIBRARY_PATH=$(pwd)/build/%{rust_triple}/stage2/lib:$LD_LIBRARY_PATH

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

%if %{with bundled_llvm}
export CC="gcc -fuse-ld=lld"
export CXX="g++ -fuse-ld=lld"
%endif

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
rm -f %{buildroot}%{_docdir}/%{name}/html/FiraSans-Medium.woff2
rm -f %{buildroot}%{_docdir}/%{name}/html/FiraSans-Regular.woff2
rm -f %{buildroot}%{_docdir}/%{name}/html/SourceCodePro-It.ttf.woff2
rm -f %{buildroot}%{_docdir}/%{name}/html/SourceCodePro-Regular.ttf.woff2
rm -f %{buildroot}%{_docdir}/%{name}/html/SourceCodePro-Semibold.ttf.woff2
rm -f %{buildroot}%{_docdir}/%{name}/html//SourceSerif4-Bold.ttf.woff2
rm -f %{buildroot}%{_docdir}/%{name}/html/SourceSerif4-It.ttf.woff2
rm -f %{buildroot}%{_docdir}/%{name}/html/SourceSerif4-Regular.ttf.woff2

# Sanitize the HTML documentation
#find %{buildroot}%{_docdir}/%{name}/html -empty -delete
#find %{buildroot}%{_docdir}/%{name}/html -type f -exec chmod -x '{}' '+'

# Create the path for crate-devel packages
mkdir -p %{buildroot}%{_datadir}/cargo/registry

# Cargo no longer builds its own documentation
# https://github.com/rust-lang/cargo/pull/4904
mkdir -p %{buildroot}%{_docdir}/cargo
ln -sT ../rust/html/cargo/ %{buildroot}%{_docdir}/cargo/html

%if %without lldb
rm -f %{buildroot}%{_bindir}/rust-lldb
rm -f %{buildroot}%{rustlibdir}/etc/lldb_*
%endif

# We don't need the old versions...
#rm %{buildroot}%{_bindir}/*.old

# And this is definitely installed in the wrong location
#mv %{buildroot}%{_prefix}/src/etc %{buildroot}/


%if %{with tests}
%check
%{?cmake_path:export PATH=%{cmake_path}:$PATH}
%{?rustflags:export RUSTFLAGS="%{rustflags}"}

%if %{with bundled_llvm}
export CC="gcc -fuse-ld=lld"
export CXX="g++ -fuse-ld=lld"
%endif

# The results are not stable on koji, so mask errors and just log it.
%{python} ./x.py test --no-fail-fast || :
%{python} ./x.py test --no-fail-fast cargo || :
%{python} ./x.py test --no-fail-fast clippy || :
%{python} ./x.py test --no-fail-fast rls || :
%{python} ./x.py test --no-fail-fast rustfmt || :
%endif

%files
%license COPYRIGHT LICENSE-APACHE LICENSE-MIT
%doc README.md
%{_bindir}/rustc
%{_bindir}/rustdoc
%{_bindir}/rust-analyzer
%{_libdir}/*.so
%doc %{_mandir}/man1/rustc.1*
%doc %{_mandir}/man1/rustdoc.1*
%dir %{rustlibdir}
%dir %{rustlibdir}/%{rust_triple}
%dir %{rustlibdir}/%{rust_triple}/lib
%{rustlibdir}/%{rust_triple}/lib/*.so
%{rustlibdir}/%{rust_triple}/bin/*
%{_libexecdir}/rust-analyzer-proc-macro-srv

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
%{rustlibdir}/etc/lldb_*
%endif

%files doc
%doc %{_datadir}/doc/docs/html/
%doc %{_datadir}/doc/clippy/
%doc %{_datadir}/doc/rust-analyzer/
%doc %{_datadir}/doc/rustc/
%doc %{_datadir}/doc/rustfmt/

%files -n cargo
%license src/tools/cargo/LICENSE-APACHE src/tools/cargo/LICENSE-MIT src/tools/cargo/LICENSE-THIRD-PARTY
%doc src/tools/cargo/README.md
%{_bindir}/cargo
%doc %{_mandir}/man1/cargo*.1*
%{_datadir}/zsh/site-functions/_cargo
%dir %{_datadir}/cargo
%dir %{_datadir}/cargo/registry
%{_sysconfdir}/bash_completion.d/cargo

%files -n cargo-doc
%doc %{_datadir}/doc/cargo/LICENSE*
%docdir %{_docdir}/cargo
%dir %{_docdir}/cargo
%{_docdir}/cargo/html

%files -n rustfmt
%{_bindir}/rustfmt
%{_bindir}/cargo-fmt

%files -n clippy
%{_bindir}/cargo-clippy
%{_bindir}/clippy-driver

%files src
%dir %{rustlibdir}
%{rustlibdir}/src

#files analysis
#{rustlibdir}/%{rust_triple}/analysis/
#{_prefix}/libexec/rust-analyzer-proc-macro-srv
