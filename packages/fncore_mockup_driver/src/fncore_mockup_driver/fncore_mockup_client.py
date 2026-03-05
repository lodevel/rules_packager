# fncore_mockup_client.py
# FNCORE mockup client (serial 8N1). One ASCII command per line.
# Lazy-open policy: do not touch the serial link until the first command.

from dataclasses import dataclass
import re
import time
from typing import Any


_SI_VOLTAGE_RE = re.compile(r"^\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*([a-zA-Zµ]+)?\s*$")

_SI_PREFIX = {
    "y": 1e-24, "z": 1e-21, "a": 1e-18, "f": 1e-15,
    "p": 1e-12, "n": 1e-9,  "u": 1e-6,  "µ": 1e-6,
    "m": 1e-3,  "": 1.0,    "k": 1e3,   "K": 1e3,
    "M": 1e6,   "G": 1e9,   "T": 1e12,
}


def _parse_voltage(raw: str) -> float:
    m = _SI_VOLTAGE_RE.match(raw)
    if not m:
        raise ValueError(f"Invalid voltage: {raw!r}")

    value = float(m.group(1))
    unit = (m.group(2) or "V").strip()

    # Strip trailing base-unit character (V/v) to isolate the SI prefix
    if len(unit) >= 1 and unit[-1] in ("V", "v"):
        prefix = unit[:-1]
    else:
        prefix = unit  # bare prefix or bare number

    scale = _SI_PREFIX.get(prefix)
    if scale is None:
        raise ValueError(f"Unsupported SI prefix: {prefix!r} (from {unit!r})")

    return value * scale


@dataclass
class _LogEntry:
    cmd: str
    resp: str
    requested_volts: float | None = None
    code: int | None = None


class FncoreMockupClient:
    """Lazy-open FNCORE mock client.

    Behavior:
      - No serial open at construction.
      - First command triggers open() unless manual_override is True.
      - open() remains callable, but unnecessary; repeated calls are safe.
      - close() closes only if opened.

    Manual override:
      - Prints the exact command line (`MANUAL_EXEC: ...`).
      - Operator runs it on the device console.
      - For digital reads, operator must enter `0` or `1` (prompt repeats until valid).
      - For analog reads, operator may enter SI-friendly values (e.g., `500mV`, `2.40V`).
      - For writes, no response is requested; the method returns `"OK"`.
      - For `uart_send`, the operator may paste the device response line (may be empty).
    """

    def __init__(self, port, baud, timeout_s, log_list, manual_override: bool = False, max_retries: int = 3, retry_delay_ms: int = 50):
        self.port, self.baud, self.timeout_s = port, baud, timeout_s
        self.log = log_list
        self.manual = bool(manual_override)
        self.max_retries = max_retries
        self.retry_delay_ms = retry_delay_ms
        self._ser: Any = None
        self._opened = False

    # ----- lifecycle -----

    def _ensure_open(self):
        if self.manual:
            return
        if self._opened and self._ser:
            return
        self.open()  # delegate to idempotent open()

    def _retry_on_failure(self, operation_callable, operation_name: str):
        """Retry a callable operation on failure.
        
        Args:
            operation_callable: A callable that performs the operation
            operation_name: Name of the operation for logging purposes
            
        Returns:
            The result of the successful operation, or None/raises exception after all retries
        """
        if self.manual:
            return operation_callable()
        
        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                result = operation_callable()
                if result is not None:
                    return result
                # None is considered a failure
                if attempt < self.max_retries:
                    self.log.append({"retry": f"Retry {attempt}/{self.max_retries} for {operation_name} (got None)"})
                    time.sleep(self.retry_delay_ms / 1000.0)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    self.log.append({"retry": f"Retry {attempt}/{self.max_retries} for {operation_name} (exception: {str(e)})"})
                    time.sleep(self.retry_delay_ms / 1000.0)
        
        # All retries exhausted
        if last_exception:
            raise last_exception
        return None

    def open(self):
        """Idempotent. Safe to call multiple times."""
        if self.manual:
            return
        if self._opened and self._ser:
            return
        import serial

        self._ser = serial.Serial(self.port, self.baud, timeout=self.timeout_s)
        self._opened = True

    def close(self):
        if self._ser:
            try:
                self._ser.close()
            except Exception:
                pass
        self._ser = None
        self._opened = False

    # Context manager for optional with-usage
    def __enter__(self):
        # Do not force-open; keep lazy semantics
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    # ----- helpers -----

    def _prompt_exact(self, line: str) -> None:
        print(f"MANUAL_EXEC: {line}")
        print("On the device console, type exactly:\n  " + line)
        input("Press Enter here when done.")

    def _prompt_response_line(self, *, allow_empty: bool, default_ok_if_empty: bool) -> str:
        resp = input(
            "Paste the device response line (2nd line). "
            + ("May be empty." if allow_empty else "Do not leave empty.")
            + "\n> "
        )

        if resp == "":
            if not allow_empty:
                # Ask again via recursion only for the fallback path; for prompt(),
                # use allow_empty=False and let the caller enforce if needed.
                if default_ok_if_empty:
                    return "OK"
                return self._prompt_response_line(allow_empty=allow_empty, default_ok_if_empty=default_ok_if_empty)
            if default_ok_if_empty:
                return "OK"
        return resp

    def _write_readline(self, line: str, *, allow_empty: bool = True, default_ok_if_empty: bool = True) -> str:
        if self.manual:
            self._prompt_exact(line)

            # Only prompt for a response when it is meaningful.
            # For typical write operations, the device response is effectively "OK".
            if allow_empty and default_ok_if_empty:
                resp = "OK"
            else:
                resp = self._prompt_response_line(allow_empty=allow_empty, default_ok_if_empty=default_ok_if_empty)

            self.log.append({"cmd": line, "resp_echo": "", "resp": resp, "manual": True})
            return resp

        self._ensure_open()
        # After ensure_open, either we have a serial link or an exception was raised.
        self._ser.reset_input_buffer()
        self._ser.write((line + "\n").encode("ascii"))
        resp_echo = self._ser.readline().decode("ascii", errors="ignore").strip()
        resp = self._ser.readline()
        resp = resp.decode("ascii", errors="ignore")
        resp = resp.strip() or "OK"
        self.log.append({"cmd": line, "resp_echo": resp_echo, "resp": resp, "manual": False})
        return resp

    @staticmethod
    def _dac_code_12bit_3v3(volts: float) -> int:
        v = max(0.0, min(3.3, float(volts)))
        # round to nearest representable code
        return int(round(v / 3.3 * 4095))

    # ----- Commands per spec -----

    # Digital output
    def write_digital(self, TARGET: str, io_id: str, val01: int):
        line = f"writeDigital {TARGET} {io_id} {int(val01)}"
        # Writes are expected to respond OK; treat empty as OK in manual mode.
        return self._write_readline(line, allow_empty=True, default_ok_if_empty=True)

    # Digital input
    def read_digital(self, TARGET: str, io_id: str) -> int | None:
        line = f"readDigital {TARGET} {io_id}"

        if self.manual:
            self._prompt_exact(line)  # Works correctly now
            while True:
                print(f"Enter returned value for {io_id} (0/1): ", end="", flush=True)
                raw = input().strip()
                if raw in ("0", "1"):
                    val = int(raw)
                    break
                else:
                    print(f"Invalid input '{raw}'. Please enter 0 or 1.")
            self.log.append({"cmd": line, "resp_echo": "", "resp": str(val), "manual": True})
            return val

        # Automatic mode with retry
        def _do_read():
            resp = self._write_readline(line, allow_empty=False, default_ok_if_empty=False)

            # Fallback: parse the last integer in the response string
            m = re.search(r"(?:^|\s)(-?\d+)\s*$", resp)
            if m:
                try:
                    return int(m.group(1))
                except Exception:
                    pass

            # If everything fails, return None to indicate parsing failure
            return None
        
        return self._retry_on_failure(_do_read, f"read_digital_input on channel {io_id}")

    # PWM output (0–255)
    def write_pwm(self, TARGET: str, pwm_id: str, duty8bit: int):
        duty = max(0, min(255, int(duty8bit)))
        line = f"writePWM {TARGET} {pwm_id} {duty}"
        return self._write_readline(line, allow_empty=True, default_ok_if_empty=True)

    # Analog output (volts → 12-bit code for 3.3 V unipolar)
    def write_analog_volts(self, TARGET: str, dac_id: str, volts: float):
        code = self._dac_code_12bit_3v3(volts)
        line = f"writeAnalog {TARGET} {dac_id} {code}"
        resp = self._write_readline(line, allow_empty=True, default_ok_if_empty=True)

        # Augment last log entry if it's a dict.
        try:
            if self.log and isinstance(self.log[-1], dict):
                self.log[-1].update({"requested_volts": float(volts), "code": int(code)})
        except Exception:
            pass

        return {"cmd": line, "resp": resp, "requested_volts": float(volts), "code": int(code)}

    # Analog input
    def read_analog(self, TARGET: str, adc_id: str) -> float | None:
        line = f"readAnalog {TARGET} {adc_id}"

        if self.manual:
            self._prompt_exact(line)
            while True:
                raw = input(
                    f"Enter returned value for {adc_id} (SI units allowed, e.g. 2.40V, 500mV): "
                ).strip()
                try:
                    v = _parse_voltage(raw)
                    break
                except Exception:
                    continue

            self.log.append({"cmd": line, "resp_echo": "", "resp": str(v), "manual": True})
            return v

        # Automatic mode with retry
        def _do_read():
            resp = self._write_readline(line, allow_empty=False, default_ok_if_empty=False)

            # Fallback: parse the last float-looking token in the response
            m = re.search(r"(?:^|\s)([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*$", resp)
            if m:
                try:
                    return float(m.group(1))
                except ValueError:
                    pass

            # If nothing usable is found, return None
            return None
        
        return self._retry_on_failure(_do_read, f"read_analog_input on channel {adc_id}")

    # UART transmit (payload in double quotes)
    def uart_send(self, TARGET: str, uart_id: str, payload: str):
        safe = payload.replace('"', "\\\"")
        line = f'uartSend {TARGET} {uart_id} "{safe}"'

        # For UART send, allow an empty device response (string) in manual mode.
        return self._write_readline(line, allow_empty=True, default_ok_if_empty=False)

    # ----- diagnostics -----

    @property
    def opened(self) -> bool:
        return bool(self._opened and self._ser)

    # ----- autotest -----

    def autotest(self):
        """
        Autotest method to call each method in the client.
        Arguments will be specified later.
        """
        print("=== Starting FncoreMockupClient Autotest ===\n")
        
        # TODO: Specify exact arguments for each method
        # Placeholder calls with typical argument patterns
        
        # Digital operations
        print("Testing write_digital...")
        for i in range(0,75):
            self.write_digital(TARGET="DSC", io_id=f"IO#DSC{i}", val01=0)

        for i in range(0,75):
            self.write_digital(TARGET="DSC", io_id=f"IO#DSC{i}", val01=1)

        print("Testing read_digital...")

        #print(f"  Result: {result}")
        
        # PWM operations
        print("Testing write_pwm...")
        # self.write_pwm(TARGET="???", pwm_id="???", duty8bit=128)
        
        # Analog operations
        print("Testing write_analog_volts...")
        # result = self.write_analog_volts(TARGET="???", dac_id="???", volts=1.65)
        # print(f"  Result: {result}")
        
        print("Testing read_analog...")
        result = self.read_analog(TARGET="DSC", adc_id="ADC#DSC0")
        result = self.read_analog(TARGET="HXT", adc_id="ADC#HXT7")
        result = self.read_analog(TARGET="HXT", adc_id="ADC#HXT4")
        result = self.read_analog(TARGET="HXT", adc_id="ADC#HXT7")
        result = self.read_analog(TARGET="HXT", adc_id="ADC#HXT4")
        result = self.read_analog(TARGET="HXT", adc_id="ADC#HXT7")
        result = self.read_analog(TARGET="HXT", adc_id="ADC#HXT4")
        print(f"  Result: {result}")
        
        # UART operations
        print("Testing uart_send...")
        # result = self.uart_send(TARGET="???", uart_id="???", payload="test message")
        # print(f"  Result: {result}")
        
        print("\n=== Autotest Complete ===")


def main():
    """
    Main function to run the autotest.
    """
    # TODO: Configure with actual port, baud, timeout, and manual_override settings
    log = []
    client = FncoreMockupClient(
        port="COM16",  # TODO: Specify actual port
        baud=115200,
        timeout_s=1.0,
        log_list=log,
        manual_override=False  # Set to False for automated testing
    )
    
    try:
        client.autotest()
    finally:
        client.close()
    
    # Print log
    print("\n=== Test Log ===")
    for entry in log:
        print(entry)


if __name__ == "__main__":
    main()
