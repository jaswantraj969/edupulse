import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { ConfirmDialog } from '../Dialog'

function Harness({ onConfirm }: { onConfirm: () => void }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        Delete thing
      </button>
      <ConfirmDialog
        open={open}
        title="Delete thing?"
        message="This cannot be undone."
        confirmLabel="Delete"
        danger
        onConfirm={onConfirm}
        onCancel={() => setOpen(false)}
      />
    </>
  )
}

describe('ConfirmDialog', () => {
  it('is a labelled modal that traps focus and restores it on Escape', async () => {
    const user = userEvent.setup()
    render(<Harness onConfirm={() => {}} />)
    const trigger = screen.getByRole('button', { name: 'Delete thing' })
    await user.click(trigger)
    const dialog = screen.getByRole('dialog', { name: 'Delete thing?' })
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    const cancel = screen.getByRole('button', { name: 'Cancel' })
    const confirm = screen.getByRole('button', { name: 'Delete' })
    expect(cancel).toHaveFocus()
    await user.tab()
    expect(confirm).toHaveFocus()
    await user.tab()
    expect(cancel).toHaveFocus() // wrapped around
    await user.tab({ shift: true })
    expect(confirm).toHaveFocus()
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
  })

  it('calls onConfirm', async () => {
    const onConfirm = vi.fn()
    render(<Harness onConfirm={onConfirm} />)
    await userEvent.click(screen.getByRole('button', { name: 'Delete thing' }))
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }))
    expect(onConfirm).toHaveBeenCalledOnce()
  })
})
