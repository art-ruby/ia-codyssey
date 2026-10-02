// 한 선택이 끝나기 전에는 같은 선택 흐름을 다시 실행하지 않는다.
export function singleFlight() {
  let pending = false;
  return async (buttons, action) => {
    if (pending) return;
    pending = true;
    const previous = buttons.map((button) => [button, button.disabled]);
    for (const [button] of previous) button.disabled = true;
    try {
      return await action();
    } finally {
      for (const [button, disabled] of previous) button.disabled = disabled;
      pending = false;
    }
  };
}
