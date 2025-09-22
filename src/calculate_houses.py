"""
概要:
    Skyfieldを用いたハウス計算モジュール（天文学的に正確な計算式版）
主な仕様:
    - 指定日時・緯度・経度からASC/MC/12ハウスカスプを正確な天文計算で算出
    - 星座名は日本語で返却
    - Placidusハウス分割の簡易実装
制限事項:
    - Placidus計算は簡易版（正確性はpyswissephに劣る）
"""
from typing import Dict, List, Optional, Callable, Tuple
import json
from skyfield.api import Loader, Topos
from skyfield.framelib import ecliptic_frame
from datetime import datetime, timezone
import os
import numpy as np
import math
from .calculate_planets import get_zodiac_sign_jp


def calculate_houses(
    dt_utc: datetime,
    latitude: float,
    longitude: float,
    ephemeris_path: str = None,
    eph=None,
    ts=None,
    system: str = "placidus"
) -> Dict:
    """
    指定日時・緯度・経度でASC/MC/12ハウスのカスプを計算（天文学的に正確な計算式版）
    Args:
        dt_utc (datetime): UTC日時
        latitude (float): 緯度
        longitude (float): 経度
        ephemeris_path (str): DE421等のパス
        eph: Skyfield Ephemerisオブジェクト
        ts: Skyfield Timescaleオブジェクト
        system (str): ハウス分割方式（placidus/equal/koch）
    Returns:
        Dict: ASC, MC, 各ハウスカスプ情報
    制限事項:
        - Placidusは簡易版
        - Equal, Kochは本関数内で実装
    """
    # Swiss Ephemeris 経路（必要時のみ実行）
    if os.environ.get("HOUSE_ENGINE", "SKYFIELD").strip().upper() == "SWISS":
        try:
            import swisseph as swe  # type: ignore
            print("calculate_houses: ENGINE=SWISS (pyswisseph)")
            # タイムゾーン正規化
            if dt_utc.tzinfo is None:
                print("calculate_houses(swiss): WARNING naive datetime; assuming UTC")
                dt_utc = dt_utc.replace(tzinfo=timezone.utc)
            else:
                dt_utc = dt_utc.astimezone(timezone.utc)
            print(f"calculate_houses(swiss): dt_utc={dt_utc.isoformat()}")

            # 天文歴パス設定（候補を走査）
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            eph_path_candidates: List[str] = []
            env_path = os.environ.get("SWISSEPH_PATH")
            if env_path:
                eph_path_candidates.append(env_path)
            eph_path_candidates.extend([
                os.path.join("/tmp", "ephe"),  # S3から配置する優先候補
                root_dir,
                os.path.join(root_dir, "build", "ephe"),
                os.path.join(root_dir, "ephe"),
                "/opt/ephe",
                "/tmp/ephe",
            ])
            eph_dir = None
            for p in eph_path_candidates:
                if os.path.isdir(p):
                    eph_dir = p
                    break
            if eph_dir is None and env_path:
                eph_dir = env_path
            if eph_dir:
                swe.set_ephe_path(eph_dir)
                try:
                    file_list = []
                    try:
                        file_list = os.listdir(eph_dir)
                    except Exception:
                        pass
                    has_sepl18 = any(fn.lower().startswith("sepl_18") for fn in file_list)
                    has_semo18 = any(fn.lower().startswith("semo18") for fn in file_list)
                    has_deltat = any(fn.lower() == "sedeltat.txt" for fn in file_list)
                    print(f"calculate_houses(swiss): set_ephe_path dir={eph_dir}, files={len(file_list)}, sepl_18={has_sepl18}, semo18={has_semo18}, sedeltat={has_deltat}")
                except Exception:
                    pass
            # JPLのde432s.bspを優先指定（/tmp → /opt → ルート直下 → epheディレクトリ）
            try:
                jpl_candidates = [
                    "/tmp/de432s.bsp",
                    "/opt/de432s.bsp",
                    os.path.join(root_dir, "de432s.bsp"),
                ]
                if eph_dir:
                    jpl_candidates.append(os.path.join(eph_dir, "de432s.bsp"))
                jpl_file = next((p for p in jpl_candidates if os.path.isfile(p)), None)
                if jpl_file:
                    swe.set_jpl_file(jpl_file)
                    print(f"calculate_houses(swiss): using JPL BSP file={jpl_file}")
                else:
                    print("calculate_houses(swiss): WARNING de432s.bsp not found for set_jpl_file")
            except Exception as e:
                try:
                    print(f"calculate_houses(swiss): set_jpl_file failed: {e}")
                except Exception:
                    pass
            # ハウス方式
            system_map = {"placidus": b"P", "equal": b"E", "koch": b"K"}
            swe_system = system_map.get(system.lower(), b"P")
            # JDUT
            year, month, day = dt_utc.year, dt_utc.month, dt_utc.day
            hour = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0 + dt_utc.microsecond / 3_600_000_000.0
            jd_ut = swe.julday(year, month, day, hour)
            print(f"calculate_houses(swiss): jd_ut={jd_ut:.6f}, lat={latitude}, lon(E+)={longitude}, system={system}")
            # 計算
            cusps, ascmc = swe.houses(jd_ut, latitude, longitude, swe_system)
            asc_longitude = float(ascmc[0]) % 360.0
            mc_longitude = float(ascmc[1]) % 360.0
            dc_longitude = (asc_longitude + 180.0) % 360.0
            ic_longitude = (mc_longitude + 180.0) % 360.0
            try:
                sample = []
                zero_based_dbg = (len(cusps) == 12)
                for i in range(1, 5):
                    idx = (i - 1) if zero_based_dbg else i
                    sample.append((i, float(cusps[idx]) % 360.0))
                print(f"calculate_houses(swiss): ASC={asc_longitude:.6f}, MC={mc_longitude:.6f}, sample cusps={sample}")
            except Exception:
                pass
            houses_list: List[Dict[str, float | int | str]] = []
            zero_based = (len(cusps) == 12)
            for i in range(1, 13):
                idx = (i - 1) if zero_based else i
                lon = float(cusps[idx]) % 360.0
                houses_list.append({"number": i, "sign": get_zodiac_sign_jp(lon), "longitude": lon})
            return {
                "ascendant": {"sign": get_zodiac_sign_jp(asc_longitude), "longitude": asc_longitude},
                "descendant": {"sign": get_zodiac_sign_jp(dc_longitude), "longitude": dc_longitude},
                "mc": {"sign": get_zodiac_sign_jp(mc_longitude), "longitude": mc_longitude},
                "ic": {"sign": get_zodiac_sign_jp(ic_longitude), "longitude": ic_longitude},
                "houses": houses_list,
            }
        except Exception as e:
            try:
                print(f"calculate_houses: Swiss engine failed, fallback to Skyfield. error={e}")
            except Exception:
                pass
    # --- Skyfieldでの天体歴ファイル読み込み ---
    if eph is None or ts is None:
        if ephemeris_path is None:
            # Lambda環境では/tmpディレクトリも確認
            tmp_eph_path = '/tmp/de432s.bsp'
            if os.path.exists(tmp_eph_path):
                eph_path = tmp_eph_path
            else:
                root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                eph_path = os.path.join(root_dir, 'de432s.bsp')
        else:
            eph_path = ephemeris_path
        if not os.path.exists(eph_path):
            raise FileNotFoundError(f"Ephemeris file not found: {eph_path}")
        load = Loader(os.path.dirname(eph_path))
        eph = load(os.path.basename(eph_path))
        ts = load.timescale()

    # --- Skyfieldで地方恒星時（LST）を取得 ---
    t = ts.from_datetime(dt_utc)
    location = Topos(latitude_degrees=latitude, longitude_degrees=longitude)
    
    # Skyfieldから正確なLSTを取得
    observer = eph['earth'] + location
    lst_skyfield = t.gast + longitude / 15.0  # グリニッジ恒星時 + 経度補正
    
    # 度に変換（より正確な計算）
    lst_degrees = (lst_skyfield * 15.0) % 360.0
    
    # RAMC（Right Ascension of MC）
    ramc_degrees = lst_degrees
    
    # of-date の平均黄道傾斜角（IAU2006近似多項式）
    # epsilon_A = 23°26′21.448″ − 46.8150″T − 0.00059″T^2 + 0.001813″T^3
    # T: TT世紀。Skyfieldのt.ttを使用
    jd_tt = t.tt
    T = (jd_tt - 2451545.0) / 36525.0
    eps_arcsec = 21.448 - 46.8150 * T - 0.00059 * (T**2) + 0.001813 * (T**3)
    obliquity_degrees = 23.0 + 26.0/60.0 + eps_arcsec/3600.0
    
    print(f"calculate_houses: DateTime={dt_utc}")
    print(f"calculate_houses: Latitude={latitude:.4f}, Longitude={longitude:.4f}")
    print(f"calculate_houses: JD_TT={jd_tt:.6f}, T_TT={T:.6f}")
    print(f"calculate_houses: LST={lst_degrees:.4f}°, RAMC={ramc_degrees:.4f}°")
    print(f"calculate_houses: Obliquity={obliquity_degrees:.4f}°")
    
    # --- 正確なMC計算（天文学的公式） ---
    # MC = LST（地方恒星時）の黄経変換
    # tan(MC_longitude) = tan(LST) / cos(obliquity)
    ramc_rad = math.radians(ramc_degrees)
    obliquity_rad = math.radians(obliquity_degrees)
    
    # MC計算：地方恒星時から黄経への変換
    # MC = arctan2(sin(LST), cos(LST) * cos(obliquity))
    mc_longitude = math.degrees(math.atan2(
        math.sin(ramc_rad),
        math.cos(ramc_rad) * math.cos(obliquity_rad)
    )) % 360
    
    print(f"calculate_houses: MC_longitude={mc_longitude:.4f}°")
    
    # --- 正確なASC計算（天文学的公式） ---
    # tan(ASC) = -cos(RAMC) / (cos(obliquity) * sin(RAMC) + tan(latitude) * sin(obliquity))
    lat_rad = math.radians(latitude)
    
    # ASC計算の詳細デバッグ
    asc_numerator = -math.cos(ramc_rad)
    asc_denominator = math.cos(obliquity_rad) * math.sin(ramc_rad) + math.tan(lat_rad) * math.sin(obliquity_rad)
    asc_tan = asc_numerator / asc_denominator
    asc_longitude_raw = math.degrees(math.atan(asc_tan))
    
    # 四分円補正（ASC用）
    # atan2を使って正しい四分円を得る
    asc_longitude = math.degrees(math.atan2(asc_numerator, asc_denominator))
    if asc_longitude < 0:
        asc_longitude += 360
    
    # 既存の式は実質的にDESC寄りの値を返すため、ASCへ反転
    asc_longitude = (asc_longitude + 180.0) % 360.0
    
    print(f"calculate_houses: ASC_numerator={asc_numerator:.4f}, ASC_denominator={asc_denominator:.4f}")
    print(f"calculate_houses: ASC_raw={asc_longitude_raw:.4f}°, ASC_corrected={asc_longitude:.4f}°")
    
    # --- ハウス分割方式ごとのカスプ計算 ---
    houses = []
    if system == "equal":
        # イコールハウス: ASCから30度ずつ等分
        for i in range(12):
            cusp_longitude = (asc_longitude + i * 30) % 360
            houses.append({
                "number": i + 1,
                "sign": get_zodiac_sign_jp(cusp_longitude),
                "longitude": cusp_longitude
            })
    elif system == "koch":
        # Kochハウス: MCと緯度を使った簡易実装（厳密には天文計算が必要だが、ここでは近似）
        # 参考: https://en.wikipedia.org/wiki/House_(astrology)#Koch
        # 1ハウス: ASC, 10ハウス: MC, 4ハウス: MC+180, 7ハウス: ASC+180
        # 他は等分近似
        house_cusps = [
            asc_longitude,                    # 1st house = ASC
            (asc_longitude + 30) % 360,       # 2nd house
            (asc_longitude + 60) % 360,       # 3rd house
            (mc_longitude + 180) % 360,       # 4th house = IC
            (asc_longitude + 120) % 360,      # 5th house
            (asc_longitude + 150) % 360,      # 6th house
            (asc_longitude + 180) % 360,      # 7th house = DESC
            (asc_longitude + 210) % 360,      # 8th house
            (asc_longitude + 240) % 360,      # 9th house
            mc_longitude,                     # 10th house = MC
            (asc_longitude + 300) % 360,      # 11th house
            (asc_longitude + 330) % 360       # 12th house
        ]
        for i, cusp_longitude in enumerate(house_cusps):
            houses.append({
                "number": i + 1,
                "sign": get_zodiac_sign_jp(cusp_longitude),
                "longitude": cusp_longitude
            })
    else:
        # プラシーダス分割（半日弧の時間三等分を数値解）
        # 参考: Meeus ほか。方程式: α(λ) と H0(λ) を用い、各クォドラントで
        #   Quadrant I (ASC→MC): 12: α - 2/3·H0 = RAMC, 11: α - 1/3·H0 = RAMC
        #   Quadrant II (MC→Dsc):  9: α + 1/3·H0 = RAMC,  8: α + 2/3·H0 = RAMC
        #   Quadrant III(Dsc→IC):  6: α + 1/3·H0 = RAMC+180, 5: α + 2/3·H0 = RAMC+180
        #   Quadrant IV (IC→ASC):  3: α - 1/3·H0 = RAMC+180, 2: α - 2/3·H0 = RAMC+180

        def normalize_deg(x: float) -> float:
            v = x % 360.0
            return v + 360.0 if v < 0 else v

        def circ_diff(a: float, b: float) -> float:
            """円環差分: a-b を (-180,180] に正規化"""
            d = (a - b + 180.0) % 360.0 - 180.0
            return d

        def ra_dec_from_lambda(lambda_deg: float, eps_deg: float) -> Tuple[float, float]:
            """
            黄経λから赤経α・赤緯δを計算（度）
            :param lambda_deg: float 黄経
            :param eps_deg: float 黄道傾斜角
            :return: (α[deg], δ[deg])
            """
            lam = math.radians(lambda_deg)
            eps = math.radians(eps_deg)
            sinlam = math.sin(lam)
            coslam = math.cos(lam)
            # 赤緯
            sd = math.sin(eps) * sinlam
            delta = math.degrees(math.asin(sd))
            # 赤経（atan2で四分円）
            y = sinlam * math.cos(eps)
            x = coslam
            alpha = math.degrees(math.atan2(y, x))
            alpha = normalize_deg(alpha)
            return alpha, delta

        def rising_hour_angle(delta_deg: float, phi_deg: float) -> Optional[float]:
            """
            昇没時角 H0（度）を返す。存在しなければ None（周極）
            cos H0 = -tan φ · tan δ
            """
            phi = math.radians(phi_deg)
            delta = math.radians(delta_deg)
            val = -math.tan(phi) * math.tan(delta)
            if val < -1.0 or val > 1.0:
                return None
            return math.degrees(math.acos(val))

        def oblique_ascension(lambda_deg: float, eps_deg: float, phi_deg: float) -> Optional[float]:
            """
            斜昇 OA(λ) = その黄経λが昇る瞬間の LST（= α − H0）。
            H0 が未定義（周極）の場合は None。
            """
            alpha, delta = ra_dec_from_lambda(lambda_deg, eps_deg)
            h0 = rising_hour_angle(delta, phi_deg)
            if h0 is None:
                return None
            return normalize_deg(alpha - h0)

        def solve_lambda_by_OA(n_frac: float, base_ramc: float, sign_factor: float,
                               win_start: float, win_end: float, init_step_deg: float = 0.5,
                               use_descension: bool = False) -> Optional[float]:
            """
            F(λ) = (base_ramc − X(λ)) − sign_factor * n_frac * H0(λ) = 0 を
            指定ウィンドウ [win_start → win_end]（反時計回り）内で探索して二分法で解く。
            :param n_frac: 1/3 または 2/3
            :param base_ramc: RAMC or RAMC+180（度）
            :param sign_factor: +1 or −1
            :param win_start: 開始角（度）
            :param win_end: 終了角（度）
            :param use_descension: True のとき X(λ) として OD(λ)=α+H0 を使用（下半球用）
            :return: λ（度）またはNone
            """
            base = normalize_deg(base_ramc)

            def F(lam_deg: float) -> Optional[float]:
                alpha, delta = ra_dec_from_lambda(lam_deg, obliquity_degrees)
                h0 = rising_hour_angle(delta, latitude)
                if h0 is None:
                    return None
                x_val = normalize_deg(alpha + h0) if use_descension else normalize_deg(alpha - h0)
                lhs = circ_diff(base, x_val)
                rhs = sign_factor * n_frac * h0
                return lhs - rhs

            # 反時計回りにウィンドウを走査
            def iter_window(start: float, end: float, step: float):
                # 窓の開始点そのものは評価しない（境界誤検出回避）
                angle = normalize_deg(start + step)
                end_n = normalize_deg(end)
                yield angle
                # 進めて終点到達まで
                while True:
                    angle = normalize_deg(angle + step)
                    yield angle
                    if abs(circ_diff(angle, end_n)) <= step * 0.5:
                        break

            prev_lam = None
            prev_val = None
            for lam in iter_window(win_start, win_end, init_step_deg):
                val = F(lam)
                if prev_val is None or val is None or prev_lam is None:
                    prev_lam, prev_val = lam, val
                    continue
                if prev_val == 0.0:
                    return prev_lam
                if val == 0.0:
                    return lam
                if prev_val * val < 0:  # 符号反転
                    # 二分法
                    lo, hi = prev_lam, lam
                    flo, fhi = prev_val, val
                    for _ in range(30):
                        mid = (lo + hi) / 2.0
                        fmid = F(mid)
                        if fmid is None:
                            lo = mid
                            flo = fmid if fmid is not None else flo
                            continue
                        if abs(fmid) < 1e-6:
                            return normalize_deg(mid)
                        if flo * fmid <= 0:
                            hi = mid
                            fhi = fmid
                        else:
                            lo = mid
                            flo = fmid
                    return normalize_deg((lo + hi) / 2.0)
                prev_lam, prev_val = lam, val
            try:
                print(f"solve_lambda_by_OA: NO ROOT (n_frac={n_frac}, base={base:.6f}, sign={sign_factor}, window=({normalize_deg(win_start):.6f}->{normalize_deg(win_end):.6f}), step={init_step_deg}, use_descension={use_descension})")
            except Exception:
                pass
            return None

        # フォールバック: 窓内を高密度サンプリングして |F| 最小解を近似、必要ならセカントで改善
        def solve_with_fallback(n_frac: float, base_ramc: float,
                                win_start: float, win_end: float,
                                use_descension: bool,
                                sign_factor_opts: List[float] = [+1.0, -1.0],
                                sample_step: float = 0.05) -> Optional[float]:
            base = normalize_deg(base_ramc)

            def F_val(lam_deg: float, sign_factor: float) -> Optional[float]:
                alpha, delta = ra_dec_from_lambda(lam_deg, obliquity_degrees)
                h0 = rising_hour_angle(delta, latitude)
                if h0 is None:
                    return None
                x_val = normalize_deg(alpha + h0) if use_descension else normalize_deg(alpha - h0)
                lhs = circ_diff(base, x_val)
                rhs = sign_factor * n_frac * h0
                return lhs - rhs

            # サンプリング
            best: Optional[Tuple[float, float, float]] = None  # (absF, lam, sign)
            angle = normalize_deg(win_start)
            end_n = normalize_deg(win_end)
            guard = 0
            while True:
                for s in sign_factor_opts:
                    fv = F_val(angle, s)
                    if fv is not None:
                        af = abs(fv)
                        if (best is None) or (af < best[0]):
                            best = (af, angle, s)
                angle = normalize_deg(angle + sample_step)
                guard += 1
                if abs(circ_diff(angle, end_n)) <= sample_step * 0.5 or guard > int(360.0 / sample_step) + 5:
                    break
            if best is None:
                return None
            _, lam0, s0 = best
            # セカント法で微修正
            lam1 = normalize_deg(lam0 + sample_step)
            f0 = F_val(lam0, s0)
            f1 = F_val(lam1, s0)
            if f0 is None or f1 is None:
                return lam0
            for _ in range(20):
                if f1 - f0 == 0:
                    break
                lam2 = normalize_deg(lam1 - f1 * (lam1 - lam0) / (f1 - f0))
                # ウィンドウ外に飛んだらクリップ
                # 反時計回りで start->end の範囲に丸める
                if circ_diff(lam2, win_start) < 0 or circ_diff(win_end, lam2) < 0:
                    lam2 = normalize_deg((win_start + win_end) / 2.0)
                f2 = F_val(lam2, s0)
                if f2 is None:
                    break
                lam0, f0 = lam1, f1
                lam1, f1 = lam2, f2
                if abs(f1) < 1e-6:
                    return lam1
            return lam1

        # 各クォドラントの探索ウィンドウを設定（反時計回り）
        def win_ccw(start: float, end: float) -> Tuple[float, float]:
            return (normalize_deg(start), normalize_deg(end))

        # 主要点
        asc = normalize_deg(asc_longitude)
        mc = normalize_deg(mc_longitude)
        dsc = normalize_deg(asc + 180.0)
        ic = normalize_deg(mc + 180.0)

        # クォドラント（ハウス順の反時計回り）
        win_asc_ic = win_ccw(asc, ic)   # 2,3
        win_ic_dsc = win_ccw(ic, dsc)   # 5,6
        win_dsc_mc = win_ccw(dsc, mc)   # 8,9
        win_mc_asc = win_ccw(mc, asc)   # 11,12
        win_ic_asc = win_ccw(ic, asc)   # 3,2
        try:
            print(f"calculate_houses: windows asc->ic={win_asc_ic}, ic->dsc={win_ic_dsc}, dsc->mc={win_dsc_mc}, mc->asc={win_mc_asc}")
        except Exception:
            pass

        # 各カスプを解く（順序と窓を狭めて一意に選ぶ）
        cusp_values: List[Tuple[int, Optional[float]]] = []
        # 1,10は既存
        c1 = normalize_deg(asc_longitude)
        cusp_values.append((1, c1))
        # 11: MC→ASC（先に1/3、次に2/3）
        try:
            print(f"solve C11: base=RAMC={ramc_degrees:.6f}, n_frac=2/3, sign=+1, window={win_mc_asc}, use_descension=False")
        except Exception:
            pass
        c11 = solve_lambda_by_OA(n_frac=2.0/3.0, base_ramc=ramc_degrees, sign_factor=+1.0,
                                 win_start=win_mc_asc[0], win_end=win_mc_asc[1])
        cusp_values.append((11, c11))
        # 12: 11→ASC
        try:
            print(f"solve C12: base=RAMC={ramc_degrees:.6f}, n_frac=1/3, sign=+1, window=({c11 if c11 is not None else win_mc_asc[0]}, {win_mc_asc[1]}), use_descension=False")
        except Exception:
            pass
        c12 = solve_lambda_by_OA(n_frac=1.0/3.0, base_ramc=ramc_degrees, sign_factor=+1.0,
                                 win_start=c11 if c11 is not None else win_mc_asc[0], win_end=win_mc_asc[1])
        cusp_values.append((12, c12))
        # 10
        c10 = normalize_deg(mc_longitude)
        cusp_values.append((10, c10))
        # 9/8 は 3/2 の対向で保証
        c9 = None
        c8 = None
        # 7
        c7 = normalize_deg(asc_longitude + 180.0)
        cusp_values.append((7, c7))
        # 6/5 は 12/11 の対向で保証
        c6 = None
        c5 = None
        # 4
        c4 = normalize_deg(mc_longitude + 180.0)
        cusp_values.append((4, c4))
        # 3: ASC→IC（半夜弧：OD=α+H0 使用, 基準 RAMC+180, f=2/3）
        try:
            print(f"solve C3: base=RAMC+180={normalize_deg(ramc_degrees+180.0):.6f}, n_frac=2/3, sign=+1, window={win_asc_ic}, use_descension=True")
        except Exception:
            pass
        c3 = solve_lambda_by_OA(n_frac=2.0/3.0, base_ramc=ramc_degrees + 180.0, sign_factor=+1.0,
                               win_start=win_asc_ic[0], win_end=win_asc_ic[1], init_step_deg=0.1,
                               use_descension=True)
        if c3 is None:
            c3 = solve_with_fallback(n_frac=2.0/3.0, base_ramc=ramc_degrees + 180.0,
                                      win_start=win_asc_ic[0], win_end=win_asc_ic[1],
                                      use_descension=True)
        cusp_values.append((3, c3))
        # 2: ASC→IC（半夜弧：OD 使用, 基準 RAMC+180, f=1/3。窓は ASC→c3 に狭める）
        try:
            print(f"solve C2: base=RAMC+180={normalize_deg(ramc_degrees+180.0):.6f}, n_frac=1/3, sign=+1, window=({win_asc_ic[0]}, {c3 if c3 is not None else win_asc_ic[1]}), use_descension=True")
        except Exception:
            pass
        c2 = solve_lambda_by_OA(n_frac=1.0/3.0, base_ramc=ramc_degrees + 180.0, sign_factor=+1.0,
                               win_start=win_asc_ic[0], win_end=(c3 if c3 is not None else win_asc_ic[1]), init_step_deg=0.1,
                               use_descension=True)
        if c2 is None:
            c2 = solve_with_fallback(n_frac=1.0/3.0, base_ramc=ramc_degrees + 180.0,
                                      win_start=win_asc_ic[0], win_end=(c3 if c3 is not None else win_asc_ic[1]),
                                      use_descension=True)
        cusp_values.append((2, c2))

        # 対向で補完
        # 7,4,10 は既存
        # 5=11+180, 6=12+180, 8=2+180, 9=3+180
        # 既存値を辞書化
        cv_map: Dict[int, Optional[float]] = {num: val for num, val in cusp_values}
        if cv_map.get(11) is not None:
            cv_map[5] = normalize_deg(cv_map[11] + 180.0)  # type: ignore
        if cv_map.get(12) is not None:
            cv_map[6] = normalize_deg(cv_map[12] + 180.0)  # type: ignore
        if cv_map.get(2) is not None:
            cv_map[8] = normalize_deg(cv_map[2] + 180.0)   # type: ignore
        if cv_map.get(3) is not None:
            cv_map[9] = normalize_deg(cv_map[3] + 180.0)   # type: ignore

        cusp_values = sorted([(k, v) for k, v in cv_map.items()], key=lambda x: x[0])
        # デバッグ: 数値解が得られなかったカスプ（Equalフォールバック候補）
        try:
            missing = [k for k, v in cusp_values if v is None]
            if missing:
                print(f"calculate_houses: Placidus solver missing cusps (fallback to Equal): {missing}")
        except Exception:
            pass

        # 欠損（None）はEqualでフォールバック
        equal_fallback = [(normalize_deg(asc_longitude + i * 30.0)) for i in range(12)]

        # 1..12順に整形（欠損はEqualでフォールバック）
        number_to_long: Dict[int, float] = {}
        for i in range(1, 13):
            val = cv_map.get(i)
            if val is None:
                lon = equal_fallback[(i - 1) % 12]
            else:
                lon = normalize_deg(val)
            number_to_long[i] = lon

        for i in range(1, 13):
            lon = number_to_long[i]
            houses.append({
                "number": i,
                "sign": get_zodiac_sign_jp(lon),
                "longitude": lon
            })
    
    # --- 結果の返却 ---
    # DCとICの計算
    dc_longitude = (asc_longitude + 180) % 360  # ASCの対向
    ic_longitude = (mc_longitude + 180) % 360   # MCの対向
    
    result = {
        "ascendant": {
            "sign": get_zodiac_sign_jp(asc_longitude),
            "longitude": asc_longitude
        },
        "descendant": {
            "sign": get_zodiac_sign_jp(dc_longitude),
            "longitude": dc_longitude
        },
        "mc": {
            "sign": get_zodiac_sign_jp(mc_longitude),
            "longitude": mc_longitude
        },
        "ic": {
            "sign": get_zodiac_sign_jp(ic_longitude),
            "longitude": ic_longitude
        },
        "houses": houses
    }

    # 参照比較ログ（環境変数 HOUSE_REF_CUSPS にJSON配列で絶対黄経または {number, longitude} の配列を渡す）
    try:
        ref_env = os.environ.get("HOUSE_REF_CUSPS")
        if ref_env:
            ref_vals_raw = json.loads(ref_env)
            ref_map: Dict[int, float] = {}
            if isinstance(ref_vals_raw, list):
                if ref_vals_raw and isinstance(ref_vals_raw[0], dict):
                    for item in ref_vals_raw:
                        n = int(item.get("number"))
                        ref_map[n] = float(item.get("longitude")) % 360.0
                else:
                    # 単純配列（index 0 が house1）
                    for idx, val in enumerate(ref_vals_raw, start=1):
                        if idx > 12:
                            break
                        ref_map[idx] = float(val) % 360.0
            # 計算値マップ
            calc_map: Dict[int, float] = {h["number"]: float(h["longitude"]) % 360.0 for h in houses}

            def circ_delta(a: float, b: float) -> float:
                d = (a - b + 180.0) % 360.0 - 180.0
                return d

            diffs = []
            for n in range(1, 13):
                if n in ref_map:
                    d = circ_delta(calc_map.get(n, float('nan')), ref_map[n])
                    diffs.append({"house": n, "calc": calc_map.get(n), "ref": ref_map[n], "delta_deg": d})
            if diffs:
                print("calculate_houses: Comparison to HOUSE_REF_CUSPS (deg):")
                for row in diffs:
                    print(f"  H{row['house']:02d}: calc={row['calc']:.6f}, ref={row['ref']:.6f}, Δ={row['delta_deg']:+.6f}")
    except Exception as e:
        try:
            print(f"calculate_houses: HOUSE_REF_CUSPS compare failed: {e}")
        except Exception:
            pass

    return result
