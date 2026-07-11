import { onBeforeUnmount, onMounted, type Ref } from 'vue'

/** Calls `handler` when a click/touch happens outside the given element ref. */
export function onClickOutside(target: Ref<HTMLElement | null>, handler: () => void) {
  function listener(event: MouseEvent) {
    const el = target.value
    if (!el || el.contains(event.target as Node)) return
    handler()
  }

  onMounted(() => document.addEventListener('click', listener, true))
  onBeforeUnmount(() => document.removeEventListener('click', listener, true))
}
