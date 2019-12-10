python -m bindgen -n 7 -v parse ocp.toml out.pkl && python -m bindgen -n 7 -v transform ocp.toml out.pkl out_f.pkl && python -m bindgen -n 7 -v generate ocp.toml out_f.pkl
