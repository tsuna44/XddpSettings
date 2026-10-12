#ifndef MACROS_H
#define MACROS_H
// #define MY_API garbage(1)
/* #define MY_INLINE not_a_decorator(2)
#define MY_NS_BEGIN namespace wrong { namespace x {
*/
#define MY_NAMESPACE mylib
#define MY_NS_BEGIN namespace MY_NAMESPACE {
#define MY_NS_END }
#define MY_NESTED_BEGIN namespace outer::inline v1 {
#define MY_NESTED_END }
#define MY_INLINE inline
#ifdef MY_SHARED
#  define MY_API __attribute__((visibility("default")))
#else
#  define MY_API
#endif
#define MY_VIS(value) __attribute__((visibility(value)))
#define MY_EXPORT MY_VIS("default")
#define MY_ALIAS MY_INLINE
#define MY_NODISCARD [[nodiscard]]
#define VIRTUAL virtual
#ifdef MAYBE
#  define MAYBE_VIRTUAL virtual
#  define SOME_STATIC static inline
#  define ALL_STATIC static inline
#else
#  define MAYBE_VIRTUAL
#  define SOME_STATIC inline
#  define ALL_STATIC static
#endif
#define BAD_DECOR _NOT_DEFINED_HERE
#ifdef X1
#  define MIXED_DECOR inline
#else
#  define MIXED_DECOR 1
#endif
#ifdef MY_MODULE
#  define MY_BEGIN_EXPORT export {
#  define MY_END_EXPORT }
#else
#  define MY_BEGIN_EXPORT
#  define MY_END_EXPORT
#endif
#ifdef ASYM_MODULE
#  define ASYM_BEGIN_EXPORT export {
#else
#  define ASYM_BEGIN_EXPORT
#endif
#define ASYM_END_EXPORT }
#ifdef MY_NO_EXCEPTIONS
#  define MY_TRY
#  define MY_CATCH
#else
#  define MY_TRY try
#  define MY_CATCH catch (const std::exception &) { }
#endif
#ifdef LONG_NS
#  define NSX_BEGIN namespace long_name {
#  define NSX_END }
#else
#  define NSX_BEGIN namespace a { namespace b {
#  define NSX_END } }
#endif
#define MY_FEATURE
#define LONG_DEF \
    inline
#endif
