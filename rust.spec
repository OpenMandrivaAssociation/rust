# Fix to work around missing (not required) dependency
# libpthread.so.0(GLIBC_PRIVATE)
%global __requires_exclude libpthread.so.0
# Don't bytecompile python bits -- they're python2
%global _python_bytecompile_build 0
%define debug_package %{nil}
%define _disable_lto 1
%define _disable_ld_no_undefined 1
# To avoid undefined symbols
%define _find_debuginfo_opts -g

# (tpg) enable it if you want to build without system-wide rust and cargo
%bcond_with bootstrap
# (tpg) accordig to Rust devs a LLVM-5.0.0 is not yet supported
%bcond_with llvm
%define oname rustc

# Only x86_64 and i686 are Tier 1 platforms at this time.
# https://forge.rust-lang.org/platform-support.html
%global rust_arches znver1 x86_64 %ix86 armv7hnl armv7hl aarch64

Summary:	A safe, concurrent, practical programming language
Name:		rust
Version:	1.28.0
Release:	1
Group:		Development/Other
License:	MIT
Url:		http://www.rust-lang.org/
Source0:	http://static.rust-lang.org/dist/%{oname}-%{version}-src.tar.gz
Source100:	rust.rpmlintrc

# https://github.com/rust-lang/rust/issues/51650
# https://github.com/rust-lang-nursery/error-chain/pull/247
Patch2:		0001-Fix-new-renamed_and_removed_lints-warning-247.patch

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
%if %{without bootstrap}
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

cd src/vendor/error-chain
%patch2 -p1
cd -

%if %{with llvm}
rm -rf src/llvm/
%endif

%build
%setup_compile_flags

# We're going to override --libdir when configuring to get rustlib into a
# common path, but we'll fix the shared libraries during install.
%global common_libdir %{_prefix}/lib
%global rustlibdir %{common_libdir}/rustlib

%ifarch %{ix86} %{arm}
# On 32-bit platforms, the linker barfs because the symbol table doesn't fit
# into the available address space -- so we use -g0 for now
export CFLAGS="%{optflags} -g0"
export CXXFLAGS="%{optflags} -g0"
export LDFLAGS="%{optflags} -g0"
%else
export CFLAGS="%{optflags}"
export CXXFLAGS="%{optflags}"
export LDFLAGS="%{optflags}"
%endif

%if !%{with llvm}
mkdir omv_build_comp
export CC=gcc
export CXX=g++
# for some reason parts of the code still use cc call rather than the environment
# which results in a mixture
ln -s $(which gcc) omv_build_comp/cc
ln -s $(which g++) omv_build_comp/g++
export PATH=$PWD/omv_build_comp:$PATH
%endif

export RUST_BACKTRACE=1
export RUSTFLAGS="-Clink-arg=-Wl,-z,relro,-z,now"

# Fix up checksums for patched files
sed -i -e 's,0adc37e316f45d57d56d76245c76942d2a894643c4d2da744639d33c3cd99099,d70375a92fe18313f6a36dbd5bf2d4cb7540816a12a63d59a1ec97fbbf4923a7,;s,2382d555f809c4d7f33e739dff7aa75b2fb3c1629ca2afaa38ff4279,557902a0662f21e8842bd721eb93eec3160b66ed0005245b0bdcf4b044b2b7ac,;s,5fc674d965746f3ea1a6ea65f82352c40b83439004480bf5a338748a90e476cc,2d498a036b400dcefd59fa8ba952577956e59dca94080e7abb8a4d5a8b592c57,;s,538c6f7a557902a0662f21e8842bd721eb93eec3160b66ed0005245b0bdcf4b044b2b7ac,557902a0662f21e8842bd721eb93eec3160b66ed0005245b0bdcf4b044b2b7ac,' src/vendor/error-chain/.cargo-checksum.json

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
	--disable-codegen-tests \
	--disable-debuginfo \
	--disable-debuginfo-lines \
	--disable-debuginfo-tools \
	--disable-debuginfo-only-std \
	--build=%{rust_triple} \
	--host=%{rust_triple} \
	--target=%{rust_triple} \
	--default-linker=gcc \
%if %{with llvm}
	--enable-llvm-link-shared \
	--llvm-root=%{_prefix} \
%else
	--disable-llvm-link-shared \
%endif
	--enable-optimize \
%if %{without bootstrap}
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
%doc %{_docdir}/%{name}
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
%{rustlibdir}/%{rust_triple}/codegen-backends
%dir %{rustlibdir}/etc
%{rustlibdir}/etc/*.py
%{_mandir}/man*/*

%files src
%dir %{rustlibdir}/src
%{rustlibdir}/src/*
