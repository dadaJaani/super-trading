import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Candle } from '../entities/candle.entity';

@Injectable()
export class CandlesService {
  constructor(
    @InjectRepository(Candle)
    private readonly candlesRepository: Repository<Candle>,
  ) {}

  async findCandles(
    instrument: string,
    granularity: string,
    limit = 120,
  ) {
    const rows = await this.candlesRepository.find({
      where: { instrument, granularity },
      order: { time: 'DESC' },
      take: limit,
    });

    return rows
      .reverse()
      .map((row) => ({
        time: row.time,
        instrument: row.instrument,
        granularity: row.granularity,
        open: Number(row.open ?? 0),
        high: Number(row.high ?? 0),
        low: Number(row.low ?? 0),
        close: Number(row.close ?? 0),
        volume: row.volume ?? 0,
      }));
  }
}
