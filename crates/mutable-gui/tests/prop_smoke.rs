//! Foundation smoke test of the property category.

use proptest::prelude::*;

proptest! {
    #![proptest_config(ProptestConfig { cases: 256, ..ProptestConfig::default() })]

    #[test]
    fn json_round_trip_of_a_pair(pair: (u32, String)) {
        let text = serde_json::to_string(&pair).unwrap();
        let back: (u32, String) = serde_json::from_str(&text).unwrap();
        prop_assert_eq!(back, pair);
    }
}
