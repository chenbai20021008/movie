import { onBeforeUnmount, onMounted, watch } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart, LineChart, ScatterChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TooltipComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  BarChart,
  LineChart,
  ScatterChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkLineComponent,
  MarkAreaComponent,
  CanvasRenderer,
])

export const CHART_FONT =
  '"Inter", "PingFang SC", "Microsoft YaHei", system-ui, -apple-system, "Segoe UI", sans-serif'

/**
 * 轻量 ECharts 封装：挂载即渲染、尺寸变化自动 resize、卸载自动释放
 * @param {() => object|null} getOption 返回完整 option 的函数
 * @param {() => any} source 依赖的数据 getter，变化时重绘
 */
export function useChart(elRef, getOption, source) {
  let chart = null
  let observer = null

  const render = () => {
    if (!chart) return
    const option = getOption()
    if (!option) return
    chart.setOption(option, true)
  }

  onMounted(() => {
    if (!elRef.value) return
    chart = echarts.init(elRef.value, null, { renderer: 'canvas' })
    render()
    observer = new ResizeObserver(() => chart && chart.resize())
    observer.observe(elRef.value)
  })

  watch(source, render, { deep: true })

  onBeforeUnmount(() => {
    observer?.disconnect()
    observer = null
    chart?.dispose()
    chart = null
  })

  return { render, getChart: () => chart }
}
